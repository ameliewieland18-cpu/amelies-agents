// HTML report layout and print styling for Gotenberg.
// Example: html = buildHtmlReport(jobs, generatedAt);
function buildHtmlReport(jobs, generatedAt) {
const htmlSections = jobs.map((job, index) => `
  <section class="job-entry">
    <h2>${index + 1}. ${escapeHtml(normalize(job.role))} at ${escapeHtml(normalize(job.company))}</h2>
    <p class="meta"><strong>Found at:</strong> ${escapeHtml(normalize(job.found_at))}</p>
    <p class="meta"><strong>Link:</strong> <a href="${escapeHtml(normalize(job.link))}">${escapeHtml(normalize(job.link))}</a></p>
    <div class="description">${escapeHtml(normalize(job.full_description, 'No description available.')).replace(/\n/g, '<br>')}</div>
  </section>
`).join('\n');

const htmlReport = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Job Search Report</title>
    <style>
      body {
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        color: #1f2937;
        margin: 40px;
        line-height: 1.6;
      }
      h1 {
        margin-bottom: 8px;
        font-size: 30px;
      }
      .summary {
        color: #4b5563;
        margin-bottom: 28px;
      }
      .job-entry {
        margin-bottom: 32px;
        padding-bottom: 24px;
        border-bottom: 1px solid #d1d5db;
        page-break-inside: avoid;
      }
      .job-entry:last-child {
        border-bottom: none;
      }
      h2 {
        margin-bottom: 10px;
        font-size: 22px;
      }
      .meta {
        margin: 4px 0;
      }
      .description {
        margin-top: 14px;
        white-space: normal;
      }
      a {
        color: #0f766e;
        text-decoration: none;
      }
    </style>
  </head>
  <body>
    <h1>Job Search Report</h1>
    <p class="summary">Generated at ${escapeHtml(generatedAt)}<br>Total jobs: ${jobs.length}</p>
    ${htmlSections || '<p>No jobs available.</p>'}
  </body>
</html>`;

return htmlReport;
}
