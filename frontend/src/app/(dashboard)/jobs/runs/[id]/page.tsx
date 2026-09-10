import { WorkflowRunDetail } from "@/features/workflow/components/workflow-run-detail";

export default async function WorkflowRunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <WorkflowRunDetail runId={id} />;
}
