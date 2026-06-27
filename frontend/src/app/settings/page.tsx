import { PageHeader } from "@/components/page-header";
import { SettingsForm } from "@/components/settings-form";
import { getSettings } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const settings = await getSettings();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="LLM configuration, subreddit targets, and pipeline controls."
      />
      <SettingsForm initial={settings} />
    </div>
  );
}
