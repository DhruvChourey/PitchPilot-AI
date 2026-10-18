import LeadDetailClient from "./LeadDetailClient";

// This route always fetches a specific lead by id at runtime -- there's
// no static shell to prerender, so it's explicitly opted out of Next.js
// 16's "instant navigation" validation rather than forced into a
// Suspense/"use cache" shape that wouldn't fit a single-record detail page.
export const instant = false;

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <LeadDetailClient id={id} />;
}
