/*
  Typed-answer matching.
  Later milestones add typo tolerance and mix-up detection here.
*/

// Makes typed answers comparable: lowercase, no accents, no punctuation,
// "&" -> "and", "St." -> "Saint", and a leading "the" is ignored.
export function normalize(text) {
  return (text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/&/g, 'and')
    .replace(/\bst\b/g, 'saint')
    .replace(/[^a-z0-9 ]/g, '')
    .replace(/^the /, '')
    .replace(/\s+/g, ' ')
    .trim();
}
