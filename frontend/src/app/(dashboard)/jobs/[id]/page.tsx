import { WorkflowDetail } from "@/features/workflow/components/workflow-detail";

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <WorkflowDetail workflowId={id} />;
}
