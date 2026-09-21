// Sort jobs, create both document formats, and name the output files.
const jobs = [...items.map((item) => item.json)].sort((left, right) => {
  const leftTime = left.found_at ? new Date(left.found_at).getTime() : 0;
  const rightTime = right.found_at ? new Date(right.found_at).getTime() : 0;
  return rightTime - leftTime;
});

const generatedAt = new Date().toISOString();
const markdownReport = buildMarkdownReport(jobs, generatedAt);
const htmlReport = buildHtmlReport(jobs, generatedAt);

return [{
  json: {
    generated_at: generatedAt,
    job_count: jobs.length,
    markdown_path: '/files/reports/job-search-report.md',
    pdf_path: '/files/reports/job-search-report.pdf',
    report_markdown: markdownReport,
    report_html: htmlReport,
  },
}];
