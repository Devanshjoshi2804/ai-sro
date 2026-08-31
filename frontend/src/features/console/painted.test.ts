import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * What the console's inline styles cannot be trusted to get right on their own.
 *
 * Three hundred-odd `style={{}}` objects paint this feature, and a stylesheet
 * cannot reach inside one to correct it. Two mistakes in there are invisible
 * until somebody opens the screen in the right state, and both have already
 * shipped once:
 *
 * - a bubble whose background and text ended up the same token, which happened
 *   when a literal-for-token pass mapped a near-white *foreground* onto the
 *   body text colour;
 * - `outline: "none"`, which no `:focus-visible` rule can outrank, and which
 *   left every control on the console invisible to a keyboard.
 *
 * Reading the source is the honest way to check both: they are properties of
 * the code rather than of any one rendered state, and the state that reveals
 * them is one nobody thinks to open.
 */
const HERE = join(process.cwd(), "src/features/console");

function sources(): { name: string; text: string }[] {
  return readdirSync(HERE)
    .filter((name) => name.endsWith(".tsx") && !name.endsWith(".test.tsx"))
    .map((name) => ({ name, text: readFileSync(join(HERE, name), "utf8") }));
}

describe("what the console paints", () => {
  it("never sets a background and its text to the same colour", () => {
    const invisible: string[] = [];
    for (const { name, text } of sources()) {
      const lines = text.split("\n");
      lines.forEach((line, index) => {
        const background = /background: (ink\.\w+|"#\w+")/.exec(line);
        if (!background) return;
        // Within a style object, which is a handful of lines either side.
        for (let near = Math.max(0, index - 3); near < Math.min(lines.length, index + 4); near++) {
          if (near === index) continue;
          const colour = /\bcolor: (ink\.\w+|"#\w+")/.exec(lines[near]);
          if (colour && colour[1] === background[1]) {
            invisible.push(`${name}:${index + 1} — both are ${background[1]}`);
          }
        }
      });
    }
    expect(invisible).toEqual([]);
  });

  it("never kills a focus ring inline, where no stylesheet can put it back", () => {
    const blinded = sources().flatMap(({ name, text }) =>
      text
        .split("\n")
        .map((line, index) => ({ line, index }))
        .filter(({ line }) => /outline:\s*"none"/.test(line))
        .map(({ index }) => `${name}:${index + 1}`),
    );
    expect(blinded).toEqual([]);
  });
});
