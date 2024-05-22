import data from "../tests/data.json";
import { expect, test } from "bun:test";
import { parse } from ".";

const { ids, templates } = data as Record<
  string,
  Record<string, Record<string, unknown>>
>;

test("parse is parsing as expected", () => {
  for (const [id, expected] of Object.entries(ids)) {
    const template = templates[id.split("-")[0]];
    const actual = parse(id.split("-")[1], template);
    if (typeof expected.timestamp === "string") {
      expected.timestamp = new Date(expected.timestamp);
    }
    for (const key of Object.keys(expected)) {
      const value = actual[key];
      const expectedValue = expected[key];
      if (typeof expectedValue === "number" && typeof value === "number") {
        expect(value).toBeCloseTo(expectedValue, 6);
      } else {
        expect(value).toEqual(expectedValue);
      }
    }
  }
});
