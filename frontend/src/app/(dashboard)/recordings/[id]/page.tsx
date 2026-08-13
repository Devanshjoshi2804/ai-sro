import { RecordingDetail } from "@/features/recording/components/recording-detail";

export default async function RecordingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RecordingDetail recordingId={id} />;
}
