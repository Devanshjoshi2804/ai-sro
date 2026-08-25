/**
 * The schedule, in words a warehouse person can check.
 *
 * `0 7 * * 1-5` is precise, and precision nobody can read is how a trigger ends
 * up firing at seven in the morning on Sundays because a field had one wrong
 * character. So the screen offers the shapes people actually ask for, and shows
 * back in plain words whatever it is about to save -- including a hand-written
 * expression, which stays allowed because the people who want one know exactly
 * what they want.
 *
 * Pure, and tested as such: this is the part where a mistake is silent.
 */

export type Repeat = "weekdays" | "daily" | "weekly" | "custom";

const DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** A cron expression for one of the shapes the screen offers. */
export function toCron(repeat: Exclude<Repeat, "custom">, at: string, weekday: number): string {
  const [hour, minute] = at.split(":");
  const when = `${Number(minute)} ${Number(hour)}`;
  if (repeat === "weekdays") return `${when} * * 1-5`;
  if (repeat === "weekly") return `${when} * * ${weekday}`;
  return `${when} * * *`;
}

/**
 * What an expression will actually do, or `null` where this cannot say.
 *
 * `null` never blocks anything. The scheduler understands more than this does
 * -- step values, lists, ranges of months -- and refusing an expression because
 * this file cannot phrase it would be a screen deciding what the scheduler
 * supports. It says so instead, which is the honest answer.
 */
export function describe(cron: string): string | null {
  const fields = cron.trim().split(/\s+/);
  if (fields.length !== 5) return null;

  const [minute, hour, day, month, weekday] = fields;
  if (day !== "*" || month !== "*") return null;

  const everyMinutes = minute.match(/^\*\/(\d+)$/);
  if (everyMinutes && hour === "*") return `every ${everyMinutes[1]} minutes, ${onDays(weekday)}`;
  if (minute === "*" || hour === "*") return null;
  if (!/^\d+$/.test(minute) || !/^\d+$/.test(hour)) return null;

  const at = `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
  const days = onDays(weekday);
  return days === null ? null : `${days} at ${at}`;
}

function onDays(weekday: string): string | null {
  if (weekday === "*") return "every day";
  if (weekday === "1-5") return "every weekday";
  if (weekday === "0,6" || weekday === "6,0") return "at weekends";
  if (/^\d$/.test(weekday)) return `every ${DAYS[Number(weekday)]}`;
  return null;
}
