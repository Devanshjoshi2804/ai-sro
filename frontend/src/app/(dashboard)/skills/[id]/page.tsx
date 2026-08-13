import { SkillDetail } from "@/features/skill/components/skill-detail";

export default async function SkillPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SkillDetail skillId={id} />;
}
