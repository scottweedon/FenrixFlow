// White-label seam (FORK_CHANGES.md): the wrapped component is an onboarding checklist
// entirely built around starring the upstream GitHub repo and joining its Discord (plus a
// "create a flow" step already covered by the sidebar's own "New project" button) - this
// platform has neither, so it renders nothing rather than a checklist that's 2/3 dead links.
export function CustomGetStartedProgress() {
  return null;
}

export default CustomGetStartedProgress;
