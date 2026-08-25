/**
 * The schedule, and whether a person can tell what it will do.
 *
 * `0 7 * * 1-5` is exactly right and unreadable, and an unreadable schedule is
 * one that fires at seven on Sunday because a field had one wrong character.
 * Both directions are tested: what the screen builds, and what it says back
 * about an expression somebody typed.
 */

import { describe as group, expect, it } from "vitest";
import { describe, toCron } from "@/features/trigger/cron";

group("building a schedule from what somebody chose", () => {
  it("every weekday at a time", () => {
    expect(toCron("weekdays", "07:00", 1)).toBe("0 7 * * 1-5");
    expect(toCron("weekdays", "17:30", 1)).toBe("30 17 * * 1-5");
  });

  it("every day, and one day a week", () => {
    expect(toCron("daily", "06:05", 1)).toBe("5 6 * * *");
    expect(toCron("weekly", "09:00", 3)).toBe("0 9 * * 3");
  });

  it("drops the leading zero a time input gives it", () => {
    // `08:05` is what `<input type="time">` produces, and `08 05 * * *` is not
    // a schedule every scheduler reads the same way.
    expect(toCron("daily", "08:05", 1)).toBe("5 8 * * *");
  });
});

group("saying what an expression will do", () => {
  it("reads the shapes people write", () => {
    expect(describe("0 7 * * 1-5")).toBe("every weekday at 07:00");
    expect(describe("30 17 * * *")).toBe("every day at 17:30");
    expect(describe("0 9 * * 3")).toBe("every Wednesday at 09:00");
    expect(describe("0 8 * * 0,6")).toBe("at weekends at 08:00");
    expect(describe("*/15 * * * 1-5")).toBe("every 15 minutes, every weekday");
  });

  it("says nothing rather than guessing", () => {
    // The scheduler understands more than this does. Refusing what it cannot
    // phrase would be a screen deciding what the scheduler supports; saying
    // nothing is the honest answer, and the form still submits.
    expect(describe("0 7 1 * *")).toBeNull();
    expect(describe("0 7 * 3 1-5")).toBeNull();
    expect(describe("0 7 * * 1,3,5")).toBeNull();
    expect(describe("nonsense")).toBeNull();
    expect(describe("0 7 * *")).toBeNull();
  });
});
