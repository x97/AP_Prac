# AP Psychology 2017 (100 MCQs + 2 FRQs) — extraction report

- Generated: 2026-11-02T13:07:18+08:00
- Source PDF: `assets/psychology/papers/2017/2017.pdf`
- JSON: `data/content/psychology/extraction/psychology-ap-2017.json`
- Database writes: **none** (dry run)

## Summary

- MCQ: 100
- FRQ: 2
- Options per MCQ: {'5': 100}
- Answer distribution: {'A': 21, 'B': 28, 'C': 14, 'D': 17, 'E': 20}
- Rubrics: 2 (13 rubric parts)
- Assets: 15 (figures on 5 questions; option images on 2 questions)
- Option-image questions: [43, 92]
- OCR used: yes

## Checks

- Missing MCQ numbers: none
- Empty stems: none
- Empty options: none
- Answers not in options: none
- Answer/descriptor mismatches: none
- Cross-page questions: none

## Figure questions

8, 9, 22, 49, 67

## Manual corrections / review notes

- Q15(B): restored the dropped line “perspective”.
- Q26: removed the space in “chromosome 21 ?”.
- Q31(A/C/D): restored “punishment”, “negative reinforcement”, and “differential reinforcement”.
- Q43: options are image-only; text is a placeholder pointing to the cropped scatterplot.
- Q48(E): removed trailing running-footer text.
- Q63: corrected OCR “According t Jean … lack o” to “According to Jean … lack of”.
- Q66(C): removed the spurious trailing “|”.
- Q74(C/D): restored “Conversion disorder” and “Tardive dyskinesia”.
- Q77(D): restored the dropped word “creativity”.
- Q80(E): restored “Social loafing”.
- Q82(B): corrected “interterence” to “interference”.
- Q91: normalized the printed “..” separators and punctuation.
- Q92: options are image-only; text is a placeholder pointing to the cropped graph.
- Q97: restored the five answer choices from the page image.
- Q13: normalized the dash in “motives—I”.

## Known limitations

- 2017 text is OCR-derived; all pages were reviewed against rendered page images, but residual OCR typos are possible.
- The 2017 answer key table was manually transcribed because Vision OCR did not read its body.
- Q43 and Q92 options are image-only; option text is a placeholder pointing to the cropped image.

## Verification

```bash
python3 -m json.tool data/content/psychology/extraction/psychology-ap-2017.json > /dev/null
```

The JSON was generated without writing to `psychology_exam.db` or any Release.
