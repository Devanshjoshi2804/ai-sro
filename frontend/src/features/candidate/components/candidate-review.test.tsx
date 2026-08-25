/**
 * The console's side of the suggestion a model makes about two candidates.
 *
 * It rendered none of them: a person sitting at the console could see two rows
 * and nothing saying they belong together, while the same suggestion was
 * answerable in the extension's panel. What these check is that the answer is
 * askable here too, and that the one answer with something to act on -- `same`
 * about a workflow -- offers the thing it acts on.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CandidateReview } from "@/features/candidate/components/candidate-review";
import * as api from "@/features/candidate/api";

function aCandidate(over: Partial<api.TaskCandidateModel> = {}): api.TaskCandidateModel {
  return {
    id: "cnd-wms",
    title: "Close waves on wms.acme.test",
    host: "wms.acme.test",
    signature: "POST api/waves/close",
    status: "new",
    times_seen: 4,
    median_duration_ms: 32000,
    minutes_so_far: 2.1,
    first_seen: null,
    last_seen: null,
    skill_id: null,
    dismissed_reason: null,
    named_by_model: true,
    joins: [],
    episodes: [],
    ...over,
  } as api.TaskCandidateModel;
}

const WORKFLOW = {
  other_id: "cnd-erp",
  kind: "workflow",
  because: "the receipt is always written straight after",
  by_model: true,
  answered: null,
  answered_by: null,
};

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={client}>
      <CandidateReview />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("what a model noticed about two candidates", () => {
  it("is shown here, with the reason, and can be answered", async () => {
    vi.spyOn(api, "listCandidates").mockResolvedValue([
      aCandidate({ joins: [WORKFLOW] as never }),
    ]);
    const answered = vi.spyOn(api, "answerJoin").mockResolvedValue(aCandidate());

    show();
    const user = userEvent.setup();
    // The reason, not only the claim: a suggestion nobody can weigh is one
    // nobody answers.
    expect(
      await screen.findByText(/the receipt is always written straight after/),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Same task" }));

    await waitFor(() => expect(answered).toHaveBeenCalledWith("cnd-wms", "cnd-erp", "workflow", "same"));
  });

  it("offers to teach the two as one only once a person has said they are one", async () => {
    vi.spyOn(api, "listCandidates").mockResolvedValue([
      aCandidate({ joins: [WORKFLOW] as never }),
    ]);

    show();
    await screen.findByText(/the receipt is always written straight after/);

    // Nothing acts on a suggestion. Merging on the model's word would be a task
    // identity a model decided.
    expect(screen.queryByRole("button", { name: "Teach as one" })).not.toBeInTheDocument();
  });

  it("teaches the pair as one skill once somebody has", async () => {
    vi.spyOn(api, "listCandidates").mockResolvedValue([
      aCandidate({
        joins: [{ ...WORKFLOW, answered: "same", answered_by: "devansh" }] as never,
      }),
    ]);
    const merged = vi.spyOn(api, "teachTogether").mockResolvedValue({
      first_id: "cnd-wms",
      second_id: "cnd-erp",
      recording_ids: ["rec-1", "rec-2"],
      skill_id: "skl-merged",
      needs_demonstration: false,
      because: null,
    } as api.TaughtTogetherModel);

    show();
    const user = userEvent.setup();
    // Who said so, because "these two are one job" is a claim about somebody's
    // work rather than a fact the system found.
    expect(await screen.findByText(/devansh said so/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Teach as one" }));

    await waitFor(() => expect(merged).toHaveBeenCalledWith("cnd-wms", "cnd-erp"));
  });

  it("does not offer the merge on a variant somebody called the same", async () => {
    // `same` about a variant means one is a duplicate, which the answer itself
    // already settles. There is no second half to teach.
    vi.spyOn(api, "listCandidates").mockResolvedValue([
      aCandidate({
        joins: [
          { ...WORKFLOW, kind: "variant", answered: "same", answered_by: "devansh" },
        ] as never,
      }),
    ]);

    show();
    await screen.findByText(/devansh said so/);

    expect(screen.queryByRole("button", { name: "Teach as one" })).not.toBeInTheDocument();
  });
});
