# Final run versus baseline (generated)

- Files: baseline 698, final 698
- Stored characters: baseline 13,558,676, final 13,346,728
- Files only in the baseline: 0
- Files only in the final run: 0
- Recall regressions: 0

| Verdict | Baseline | Final |
|---|---|---|
| COMPLETE | 331 | 337 |
| EMPTY-AGREED | 1 | 1 |
| EMPTY-PLAUSIBLE | 140 | 88 |
| ERROR | 52 | 43 |
| NEAR-COMPLETE | 5 | 0 |
| OK-NO-ORACLE | 148 | 209 |
| PARTIAL | 1 | 0 |
| UNVERIFIABLE | 20 | 20 |

## Verdict changes

| file | baseline | final | recall before | recall after |
|---|---|---|---|---|
| `Audio/ShortAudioSampleFrench.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/de-DE_(We_Are_At_School_x2).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/en-AU_(A_Little_Bottle_Of_Water).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/en-GB_(A_Little_Bottle_Of_Water).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/en-US_(A_Little_Bottle_Of_Water).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/it-IT_(We_Are_Having_Class_x2).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/ja-JP_(We_Are_At_School).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/ko-KR_(We_Are_Having_Class_x2).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/pt-BR_(We_Are_At_School).mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/test2.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testAAC.aac` | ERROR | OK-NO-ORACLE | None | None |
| `Audio/testAACid3.aac` | ERROR | OK-NO-ORACLE | None | None |
| `Audio/testFLAC.flac` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testFLAC_commentAndNativePicture.flac` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testFLAC_coverArt.flac` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testFLAC_twoCovers.flac` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3_coverArt.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3_id3_false_aac.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3_twoCovers.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3cbrInfoTag.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3i18n.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3i18n_truncated.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3id3v1.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3id3v1_v2.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3id3v2.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3id3v24.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3lyrics.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3mpeg2.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3noid3.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3v23_twoCovers.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP3vbr.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP4.m4a` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP4_coverArt.m4a` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP4_drm.m4a` | ERROR | OK-NO-ORACLE | None | None |
| `Audio/testMP4_drm_frma.m4a` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP4_esdsFlags.m4a` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP4_truncated.m4a` | ERROR | OK-NO-ORACLE | None | None |
| `Audio/testMP4_twoCovers.m4a` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testMP4_twoSampleEntries.m4a` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testNakedUTF16BOM.mp3` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testVORBIS.ogg` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testVORBIS_coverArt.ogg` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testVORBIS_twoCovers.ogg` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testWAV.wav` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Audio/testWMA.wma` | ERROR | OK-NO-ORACLE | None | None |
| `Documents/testNPEOpenDocument.odt` | NEAR-COMPLETE | COMPLETE | 0.99 | 1.0 |
| `Documents/testODFwithOOo3.odt` | PARTIAL | COMPLETE | 0.9434 | 1.0 |
| `Documents/testODT-TIKA-6000.odt` | NEAR-COMPLETE | COMPLETE | 0.9712 | 1.0 |
| `Documents/testODTStyles3.odt` | NEAR-COMPLETE | COMPLETE | 0.9826 | 1.0 |
| `Presentations/testPPT_various2.pptx` | NEAR-COMPLETE | COMPLETE | 0.9767 | 1.0 |
| `Spreadsheets/CVLKRA-KYC_Download_File_Structure_V3.1.xlsx` | NEAR-COMPLETE | COMPLETE | 0.9947 | 1.0 |
| `Videos/en-US_(Hi).mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/ko-KR_(Annyeonghaseyo).mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testFLV.flv` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testMKV.mkv` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testMP4AudioOnly.mp4` | ERROR | OK-NO-ORACLE | None | None |
| `Videos/testMP4Video.mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testMP4VideoAudio.mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testMP4_QuickTimeMetadata.mov` | ERROR | OK-NO-ORACLE | None | None |
| `Videos/testMP4_StillImageTimeZero.mov` | ERROR | OK-NO-ORACLE | None | None |
| `Videos/testMP4_encv.mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testMP4_udtaLocation.mp4` | ERROR | OK-NO-ORACLE | None | None |
| `Videos/testVideoMp4.mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testVideo_3s.mp4` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testWEBM.webm` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testWMV.wmv` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |
| `Videos/testWMV_WMV2.wmv` | EMPTY-PLAUSIBLE | OK-NO-ORACLE | None | None |

## Recall changes (more than 0.0005)

| file | before | after | delta |
|---|---|---|---|
| `Documents/testODFwithOOo3.odt` | 0.9434 | 1.0 | +0.0566 |
| `Documents/testODT-TIKA-6000.odt` | 0.9712 | 1.0 | +0.0288 |
| `Presentations/testPPT_various2.pptx` | 0.9767 | 1.0 | +0.0233 |
| `Documents/testODTStyles3.odt` | 0.9826 | 1.0 | +0.0174 |
| `Documents/testNPEOpenDocument.odt` | 0.99 | 1.0 | +0.01 |
| `Spreadsheets/CVLKRA-KYC_Download_File_Structure_V3.1.xlsx` | 0.9947 | 1.0 | +0.0053 |

## Storage changes (more than 2 %)

| file | chars before | chars after | change |
|---|---|---|---|
| `Spreadsheets/testEXCEL_poi-61034.xlsx` | 4,556 | 227 | -95.0 % |
| `Spreadsheets/CVLKRA-KYC_Download_File_Structure_V3.1.xlsx` | 286,007 | 38,973 | -86.4 % |
| `Documents/testPDF_deeplyEmbeddedAttachments.pdf` | 155 | 243 | +56.8 % |
| `Documents/testExtraSpaces.pdf` | 176 | 264 | +50.0 % |
| `Documents/testPDF_Version.11.x.PDFA-1b.pdf` | 195 | 283 | +45.1 % |
| `Documents/testPDF_bom.pdf` | 206 | 294 | +42.7 % |
| `Documents/testPDF_Version.4.x.pdf` | 207 | 295 | +42.5 % |
| `Documents/testPDF_Version.5.x.pdf` | 207 | 295 | +42.5 % |
| `Documents/testPDF_Version.6.x.pdf` | 207 | 295 | +42.5 % |
| `Documents/testPDF_Version.7.x.pdf` | 207 | 295 | +42.5 % |
| `Documents/testPDF_Version.8.x.pdf` | 207 | 295 | +42.5 % |
| `Documents/testPDF_twoAuthors.pdf` | 207 | 295 | +42.5 % |
| `Documents/testPDF_AdobeIllustrator.pdf` | 210 | 298 | +41.9 % |
| `Documents/testColorRendering.pdf` | 130 | 184 | +41.5 % |
| `Documents/testPDF_diffTitles.pdf` | 214 | 302 | +41.1 % |
| `Documents/testFlashInPDF.pdf` | 200 | 282 | +41.0 % |
| `Documents/testPDF_Version.10.x.pdf` | 229 | 317 | +38.4 % |
| `Documents/testPDF_Version.9.x.pdf` | 231 | 319 | +38.1 % |
| `Documents/testPopupAnnotation.pdf` | 233 | 321 | +37.8 % |
| `Documents/testOCR.pdf` | 236 | 324 | +37.3 % |
| `Documents/testPDF_incrementalUpdates.pdf` | 236 | 318 | +34.7 % |
| `Documents/testPDF_JBIG2.pdf` | 262 | 350 | +33.6 % |
| `Documents/testPDFFileEmbInAnnotation_noContents.pdf` | 266 | 354 | +33.1 % |
| `Documents/testOptionalHyphen.pdf` | 233 | 307 | +31.8 % |
| `Documents/testComment.pdf` | 238 | 312 | +31.1 % |
| `Documents/testPageNumber.pdf` | 241 | 315 | +30.7 % |
| `Documents/testAnnotations.pdf` | 300 | 388 | +29.3 % |
| `Documents/testPDFTwoTextBoxes.pdf` | 266 | 340 | +27.8 % |
| `Documents/testPDFFileEmbInAnnotation.pdf` | 321 | 409 | +27.4 % |
| `Documents/testPDF_bookmarks.pdf` | 315 | 397 | +26.0 % |
| `Documents/testLinkAnnotationsButNoContents.pdf` | 88 | 109 | +23.9 % |
| `Documents/testPDF_jsActionOnPage.pdf` | 88 | 109 | +23.9 % |
| `Documents/testPDF_malformedXFA.pdf` | 88 | 109 | +23.9 % |
| `Documents/test-pdf-with-print-ticket-header.pdf` | 375 | 463 | +23.5 % |
| `Spreadsheets/testEXCEL_1img.xlsx` | 416 | 330 | -20.7 % |
| `Spreadsheets/testEXCEL_embeded.xlsx` | 416 | 330 | -20.7 % |
| `Documents/testMicrosoftIRMServices.pdf` | 438 | 526 | +20.1 % |
| `Documents/testPDF-custommetadata.pdf` | 274 | 328 | +19.7 % |
| `Documents/testAppleSingleFile.pdf` | 127 | 148 | +16.5 % |
| `Documents/testPDFTripleLangTitle.pdf` | 127 | 148 | +16.5 % |
| `Documents/testPDF_no_extract_no_accessibility_owner_empty.pdf` | 127 | 148 | +16.5 % |
| `Documents/testPDF_no_extract_yes_accessibility_owner_empty.pdf` | 127 | 148 | +16.5 % |
| `Documents/testPDF_sigflags.pdf` | 131 | 152 | +16.0 % |
| `Documents/testPDF_multiFormatEmbFiles.pdf` | 138 | 159 | +15.2 % |
| `Documents/testPDF_XMPBasicSchema.pdf` | 145 | 166 | +14.5 % |
| `Documents/testOverlappingText.pdf` | 152 | 173 | +13.8 % |
| `Documents/testPDF_PDFEncodedStringInXMP.pdf` | 155 | 176 | +13.5 % |
| `Documents/testContentStreamSpaceGlyphs.pdf` | 160 | 181 | +13.1 % |
| `Documents/testPDFPackage.pdf` | 674 | 762 | +13.1 % |
| `Documents/testPDF_acroform3.pdf` | 773 | 861 | +11.4 % |
