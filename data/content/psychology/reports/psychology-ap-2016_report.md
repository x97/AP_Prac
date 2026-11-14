# AP Psychology 2016 (100 MCQs + 2 FRQs) — extraction report

- Generated: 2026-11-02T13:06:08+08:00
- Source PDF: `assets/psychology/papers/2016/2016.pdf`
- JSON: `data/content/psychology/extraction/psychology-ap-2016.json`
- Database writes: **none** (dry run)

## Summary

- MCQ: 100
- FRQ: 2
- Options per MCQ: {'5': 100}
- Answer distribution: {'A': 15, 'B': 22, 'C': 27, 'D': 18, 'E': 18}
- Rubrics: 2 (14 rubric parts)
- Assets: 5 (figures on 5 questions; option images on 0 questions)
- Option-image questions: []
- OCR used: no

## Checks

- Missing MCQ numbers: none
- Empty stems: none
- Empty options: none
- Answers not in options: none
- Answer/descriptor mismatches: none
- Cross-page questions: none

## Figure questions

31, 64, 65, 69, 83

## Manual corrections / review notes

- Q11: restored the I-IV list to separate lines for readability.
- Q59(A): normalized “P K U” to “(PKU)”.
- Q64: normalized “S S R I s” to “SSRIs”.
- Q99(E): removed trailing “END OF SECTION I” instructions.
- Q72/Q83: rejoined line-broken hyphenated words.

## Known limitations

- Q64 and Q65 share one neuron diagram asset.
- Figure-only questions use cropped images; PDF accessibility alt text is not inserted into question context.

## Verification

```bash
python3 -m json.tool data/content/psychology/extraction/psychology-ap-2016.json > /dev/null
```

The JSON was generated without writing to `psychology_exam.db` or any Release.
