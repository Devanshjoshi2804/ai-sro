import { Console } from "@/features/console/console";
import { ThreadProvider } from "@/features/console/thread-store";

export default function ConsolePage() {
  return (
    <ThreadProvider>
      <Console />
    </ThreadProvider>
  );
}
