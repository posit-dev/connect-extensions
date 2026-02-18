import { useState } from "react";

import { type ContentItem, type Job } from "./api";
import { ContentList } from "./components/ContentList";
import { JobList } from "./components/JobList";
import { TraceView } from "./components/TraceView";

type Screen =
  | { name: "content" }
  | { name: "jobs"; content: ContentItem }
  | { name: "traces"; content: ContentItem; job: Job };

function App() {
  const [screen, setScreen] = useState<Screen>({ name: "content" });

  if (screen.name === "content") {
    return (
      <div className="min-h-screen bg-agentprism-background p-6">
        <div className="max-w-2xl mx-auto">
          <ContentList
            onSelect={(content) => setScreen({ name: "jobs", content })}
          />
        </div>
      </div>
    );
  }

  if (screen.name === "jobs") {
    return (
      <div className="min-h-screen bg-agentprism-background p-6">
        <div className="max-w-2xl mx-auto">
          <JobList
            content={screen.content}
            onSelect={(job) =>
              setScreen({ name: "traces", content: screen.content, job })
            }
            onBack={() => setScreen({ name: "content" })}
          />
        </div>
      </div>
    );
  }

  // traces screen — full-height layout managed by TraceView itself
  return (
    <TraceView
      content={screen.content}
      job={screen.job}
      onBack={() =>
        setScreen({ name: "jobs", content: screen.content })
      }
    />
  );
}

export default App;
