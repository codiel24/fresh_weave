// static/js/utils.js

/**
 * Parse a comma-separated string into an array of lowercase, trimmed strings.
 * Empty or whitespace-only segments are dropped.
 *
 * @param {string} csvString
 * @returns {string[]} lowercase tokens
 */
export function parseCsvString(csvString) {
  if (!csvString) return [];
  return csvString
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}
