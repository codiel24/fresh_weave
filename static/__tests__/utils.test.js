import { parseCsvString } from '../js/utils.js';

describe('parseCsvString', () => {
  it('splits and trims tokens, lowercases, drops empty', () => {
    expect(parseCsvString(' AI , Work,, ')).toEqual(['ai', 'work']);
  });

  it('returns empty array on empty input', () => {
    expect(parseCsvString('')).toEqual([]);
    expect(parseCsvString(null)).toEqual([]);
    expect(parseCsvString(undefined)).toEqual([]);
  });
});
