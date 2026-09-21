// Plain-text report layout.
// Example: markdown = buildMarkdownReport(jobs, generatedAt);
function buildMarkdownReport(jobs, generatedAt) {
  const markdownSections = jobs.map((job, index) => {
    const title = `${index + 1}. ${normalize(job.role)} at ${normalize(job.company)}`;
    return [
      `## ${title}`,
      '',
      `- Found at: ${normalize(job.found_at)}`,
      `- Link: ${normalize(job.link)}`,
      '',
      'Full description:',
      normalize(job.full_description, 'No description available.'),
    ].join('\n');
  }).join('\n\n---\n\n');

  const markdownReport = [
    '# Job Search Report',
    '',
    `Generated at: ${generatedAt}`,
    `Total jobs: ${jobs.length}`,
    '',
    markdownSections || '_No jobs available._',
  ].join('\n');

  return markdownReport;
}
