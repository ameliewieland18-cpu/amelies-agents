const now = new Date();
const runId = now.toISOString().replace(/[^0-9]/g, '');
const sender = 'hello.wieland.collective+manual-test@gmail.com';

return [{
  json: {
    from: 'Manual Test <' + sender + '>',
    to: 'hello.wieland.collective@gmail.com',
    subject: 'Manual responder workflow test ' + now.toISOString(),
    date: now.toISOString(),
    textPlain: [
      'Hello Wieland Collective,',
      '',
      'This is a manual test email for the automatic responder workflow.',
      'Please answer as if I am asking what services you offer and how to start a project.',
      '',
      'Thanks!',
      'Manual Test',
    ].join('\n'),
    textHtml: '',
    cc: '',
    metadata: {
      'message-id': '<manual-test-' + runId + '@n8n.local>',
    },
    attributes: {
      uid: Number(runId.slice(-12)),
    },
  },
}];
