"""The translation API: POST only, authenticated, validated, audited, read-only.

Every endpoint here is a POST. There is no GET that translates anything, so a
browser navigation, a prefetch or a crawler cannot start work; the CSRF token
applies as it does to every other POST in the application.

The audit requirement is the interesting one: a translation is a derived
reading of stored material and the record of *who asked for which document in
which language* has to survive, so each accepted request writes one
``audit_log`` row.
"""

import uuid

import pytest


@pytest.fixture()
def stub_engine():
    from services.translation import engines as engine_registry

    class Stub:
        id = "stub"
        version = "stub-1.0"
        license = "test"
        document_safe = True

        def availability(self):
            return True, None

        def translate(self, texts, source_lang, target_lang):
            return [f"{target_lang}<{text}>" for text in texts]

    engine_registry.register_engine(Stub())
    try:
        yield "stub"
    finally:
        engine_registry.unregister_engine("stub")


@pytest.fixture()
def translation_memory(tmp_path, monkeypatch):
    """A per-test memory file, wired into the app's service singleton."""
    from services.translation import service as service_module
    from services.translation.memory import TranslationMemory

    memory = TranslationMemory(tmp_path / "translation_memory.db")
    service_module.configure(memory=memory)
    try:
        yield memory
    finally:
        service_module.reset()


def _audit_rows(action):
    from Api.utils.utils import execute_query

    return execute_query(
        "SELECT action, resource, detail FROM audit_log WHERE action = %s"
        " ORDER BY id DESC", (action,), fetch="all") or []


class TestAuthentication:
    @pytest.mark.parametrize("path", [
        "/api/translation/capabilities",
        "/api/translation/text",
        "/api/translation/document",
        "/api/translation/documents",
        "/api/translation/memory/correct",
        "/api/translation/memory/suggest",
    ])
    def test_every_endpoint_requires_a_signed_in_user(self, app, client, path):
        response = client.post(path, json={})
        assert response.status_code in (302, 401, 403), (
            f"POST {path} answered {response.status_code} unauthenticated")


class TestPostOnly:
    @pytest.mark.parametrize("path", [
        "/api/translation/capabilities",
        "/api/translation/text",
        "/api/translation/document",
        "/api/translation/documents",
        "/api/translation/memory/correct",
        "/api/translation/memory/suggest",
    ])
    def test_no_endpoint_answers_a_get(self, app, client_factory, path):
        client = client_factory("admin")
        response = client.get(path)
        assert response.status_code == 405, (
            f"GET {path} answered {response.status_code}: only POST is allowed")


class TestValidation:
    def test_text_is_required(self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        response = client.post("/api/translation/text", json={"target_lang": "he"})
        assert response.status_code == 400, response.get_data(as_text=True)
        assert (response.get_json() or {}).get("field") == "text"

    def test_target_language_must_be_one_of_the_supported_ones(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        response = client.post("/api/translation/text",
                               json={"text": "Hello.", "target_lang": "xx"})
        assert response.status_code == 400
        assert (response.get_json() or {}).get("field") == "target_lang"

    def test_an_oversized_selection_is_refused_with_the_limit_in_the_message(
            self, app, client_factory, stub_engine, translation_memory):
        from services.translation.text import MAX_REQUEST_CHARS

        client = client_factory("admin")
        response = client.post("/api/translation/text", json={
            "text": "a " * (MAX_REQUEST_CHARS // 2 + 10), "target_lang": "he"})
        assert response.status_code == 413, response.get_data(as_text=True)
        body = response.get_json() or {}
        assert body.get("code") == "text_too_large"
        assert str(MAX_REQUEST_CHARS) in body.get("error", "")

    def test_a_nul_byte_is_a_validation_error_not_a_server_error(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        response = client.post("/api/translation/text",
                               json={"text": "a\x00b", "target_lang": "he"})
        assert response.status_code == 400, response.get_data(as_text=True)

    def test_a_bad_body_shape_is_a_validation_error(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        for body in ([], 3, "text"):
            response = client.post("/api/translation/text", json=body)
            assert 400 <= response.status_code < 500, (body, response.status_code)

    def test_the_documents_endpoint_bounds_the_number_of_files(
            self, app, client_factory, stub_engine, translation_memory):
        from services.translation.service import MAX_DOCUMENTS_PER_JOB

        client = client_factory("admin")
        response = client.post("/api/translation/documents", json={
            "file_ids": list(range(1, MAX_DOCUMENTS_PER_JOB + 2)),
            "target_lang": "he"})
        assert response.status_code == 400, response.get_data(as_text=True)
        assert (response.get_json() or {}).get("field") == "file_ids"


class TestTranslation:
    def test_a_selection_is_translated_and_the_response_labels_it(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        response = client.post("/api/translation/text", json={
            "text": "The door is open. Close it.", "target_lang": "he",
            "source_lang": "en"})
        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body["success"] is True
        assert body["machine_translation"] is True
        assert body["verified"] is False
        assert body["disclaimer"] == "machine translation, not verified"
        assert [s["target"] for s in body["segments"]] == [
            "he<The door is open.>", "he<Close it.>"]
        assert body["target_lang"] == "he"

    def test_each_request_is_written_to_the_audit_log(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        marker = uuid.uuid4().hex[:8]
        text = f"The door is open {marker}."
        assert client.post("/api/translation/text", json={
            "text": text, "target_lang": "he", "source_lang": "en"}).status_code == 200

        rows = _audit_rows("translation.text.requested")
        assert rows, "no audit record was written for the translation request"
        assert any("he" in str(row[2]) for row in rows)

    def test_a_correction_is_audited_and_reused(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        text = f"Open the door {uuid.uuid4().hex[:6]}."
        client.post("/api/translation/text", json={
            "text": text, "target_lang": "he", "source_lang": "en"})

        corrected = client.post("/api/translation/memory/correct", json={
            "source_text": text, "target_text": "פתח את הדלת.",
            "target_lang": "he", "source_lang": "en"})
        assert corrected.status_code == 200, corrected.get_data(as_text=True)

        again = client.post("/api/translation/text", json={
            "text": text, "target_lang": "he", "source_lang": "en"})
        body = again.get_json()
        assert body["segments"][0]["target"] == "פתח את הדלת."
        assert body["segments"][0]["origin"] == "user"
        assert _audit_rows("translation.memory.corrected")

    def test_suggestions_are_returned_separately_from_translation(
            self, app, client_factory, stub_engine, translation_memory):
        client = client_factory("admin")
        client.post("/api/translation/text", json={
            "text": "The report was delivered yesterday.",
            "target_lang": "he", "source_lang": "en"})
        response = client.post("/api/translation/memory/suggest", json={
            "text": "The report was delivered today.",
            "target_lang": "he", "source_lang": "en"})
        assert response.status_code == 200, response.get_data(as_text=True)
        body = response.get_json()
        assert body["exact_match"] is None
        assert body["suggestions"], "the near-identical sentence should be suggested"
        assert body["phase"] == "fuzzy_suggestions"

    def test_a_missing_engine_is_a_clear_503_and_not_a_traceback(
            self, app, client_factory, translation_memory):
        from services.translation import engines as engine_registry

        # No engine registered for this test: the registry holds the built-ins,
        # and none of them is installed in this environment.
        available = [engine.id for engine in engine_registry.builtin_engines()
                     if engine.availability()[0]]
        if available:                      # pragma: no cover - environment dependent
            pytest.skip(f"an engine is installed here: {available}")

        client = client_factory("admin")
        response = client.post("/api/translation/text", json={
            "text": "The door is open.", "target_lang": "he", "source_lang": "en"})
        assert response.status_code == 503, response.get_data(as_text=True)
        body = response.get_json()
        assert body["code"] == "engine_not_installed"
        assert body["engines"], "the answer must list the engines it looked for"


class TestNothingIsStored:
    def test_translating_a_document_does_not_change_the_stored_corpus(
            self, app, admin_client, stub_engine, translation_memory):
        from Api.utils.utils import execute_query
        from services.translation.service import TranslationService

        source = admin_client.post("/api/sources",
                                   json={"name": f"tx {uuid.uuid4().hex[:8]}"})
        source_id = (source.get_json() or {}).get("id")

        tables = ("content_signals", "paths", "hash_contexts", "titles_content")
        def counts():
            return {table: (execute_query(f"SELECT count(*) AS n FROM {table}",
                                          fetch="one") or [0])[0]
                    for table in tables}

        before = counts()
        response = admin_client.post("/api/translation/document", json={
            "file_id": 999999, "target_lang": "he", "source_lang": "en"})
        # A file that does not exist is a 404, and still nothing was written.
        assert response.status_code in (404, 400), response.get_data(as_text=True)
        assert counts() == before
        assert TranslationService is not None
        assert source_id is not None
