import type { TriggerModel } from "@/features/trigger/api";
import { describe as describeCron } from "@/features/trigger/cron";

/**
 * What starts a trigger, in the words a person would use.
 *
 * One function for both places that say it -- the trigger list, and the chip
 * beside a job on What we know -- because the first version of that chip said
 * "when a mail arrives" for an arrival, which is a page somebody opens.
 */
/**
 * The host a page lives on, whatever shape the address arrived in.
 *
 * An arrival's `page` is stored without a scheme -- `host/auth/realms/...` --
 * so `new URL` refuses it, and the first version of this handed back the whole
 * string: a Keycloak realm path, a hundred characters long, in the middle of a
 * sentence and inside a badge.
 */
const hostOf = (address: string | null | undefined) => {
  if (!address) return "";
  return address.replace(/^[a-z]+:\/\//i, "").split(/[/?#]/)[0];
};

/** What fires this trigger, as a sentence. */
export function firesWhen(trigger: TriggerModel): string {
  if (trigger.kind === "schedule" && trigger.cron) {
    return describeCron(trigger.cron) ?? `on the schedule ${trigger.cron}`;
  }
  if (trigger.kind === "arrival") {
    const page = hostOf(trigger.arrival?.page);
    return page ? `When an operator opens ${page}` : "When an operator opens a page";
  }
  if (trigger.kind === "watch") {
    const host = trigger.watch?.host;
    return host ? `When a matching mail arrives on ${host}` : "When a matching mail arrives";
  }
  if (trigger.kind === "inbound") return "When a message comes in";
  return "Only when somebody fires it";
}

/** The same, short enough for a badge beside a job's name. The full sentence
 *  goes in the badge's title. */
export function firesWhenShort(trigger: TriggerModel): string {
  if (trigger.kind === "schedule" && trigger.cron) {
    return describeCron(trigger.cron) ?? "on a schedule";
  }
  if (trigger.kind === "arrival") return "when its page opens";
  if (trigger.kind === "watch") return "when a mail arrives";
  if (trigger.kind === "inbound") return "on a message";
  return "manual";
}
