// Legacy email workflow behavior after bundling the readable source modules.
const assert = require('node:assert/strict');
const test = require('node:test');
const {runNode} = require('./helpers.cjs');
const workflow = 'automatic-email-responder';
const account = 'hello.wieland.collective@gmail.com';

// Example: node --test tests/workflows/*.test.cjs
test('normalization skips own mail and explains blocked senders', () => {
  assert.deepEqual(runNode(workflow, 'Normalize email', [{from: account}]), []);
  const [blocked] = runNode(workflow, 'Normalize email', [{from: 'news@mail.freelancer.com'}]);
  assert.equal(blocked.json.skip_reason, 'blocked_sender');
  assert.equal(blocked.json.blocked_sender_domain, 'freelancer.com');
  const [client] = runNode(workflow, 'Normalize email', [{
    from: {value: [{name: 'Client', address: 'CLIENT@example.com'}]},
    textHtml: '<p>Hello&nbsp;there</p>', subject: 'Question',
    date: '2026-09-21T12:00:00Z', attributes: {uid: 42},
  }]);
  assert.equal(client.json.sender_email, 'client@example.com');
  assert.equal(client.json.email_text, 'Hello there');
  assert.equal(client.json.reply_subject, 'Re: Question');
  assert.match(client.json.message_key, /^imap-uid:42:/);
});

test('unclaimed messages stop and chunking keeps the original overlap', () => {
  assert.deepEqual(runNode(workflow, 'Continue only if claimed', [{should_reply: false}]), []);
  const chunks = runNode(workflow, 'Prepare email chunks', [{email_text: 'x'.repeat(1300)}]);
  assert.deepEqual(chunks.map(item => item.json.chunk_text.length), [1200, 280]);
  assert.throws(() => runNode(workflow, 'Prepare email chunks', [{email_text: ''}]), /zero chunks/);
});

test('ranking keeps the best match for each distinct page', () => {
  const common = {email_payload: {top_k: 2}, page_id: 1};
  const pages = runNode(workflow, 'Rank top K pages', [
    {...common, distance: .4},
    {...common, distance: .1, email_chunk_index: 2},
    {...common, page_id: 2, distance: .2},
    {...common, page_id: 3, distance: 'invalid'},
  ]);
  assert.deepEqual(pages.map(item => item.json.page_id), ['1', '2']);
  assert.equal(pages[0].json.best_distance, .1);
  assert.equal(pages[0].json.matched_email_chunk_index, 2);
  assert.throws(() => runNode(workflow, 'Rank top K pages', []), /No knowledge-base/);
});

test('prompt construction uses full page content and rejects GraphQL failures', () => {
  const earlier = {'Rank top K pages': [{
    rank: 1, page_id: '1',
    email_payload: {account_email: account, full_email: 'What do you offer?'},
  }]};
  const [item] = runNode(workflow, 'Build reply prompt', [{data: {pages: {single: {
    id: 1, content: '<p>We offer design.</p>', title: 'Services',
  }}}}], earlier);
  assert.match(item.json.prompt, /We offer design\./);
  assert.match(item.json.prompt, /What do you offer\?/);
  assert.match(item.json.prompt, /do not include a subject line/);
  assert.throws(() => runNode(workflow, 'Build reply prompt', [
    {errors: [{message: 'Forbidden'}]},
  ], earlier), /Forbidden/);
});

test('all supported OpenAI output envelopes become a reply body', () => {
  const earlier = {'Build reply prompt': [{reply_subject: 'Re: Question'}]};
  const responses = [
    {output: [{content: [{text: ' Hello '}]}]},
    {output: ' Hello '}, {output_text: ' Hello '}, {text: ' Hello '},
  ];
  for (const response of responses) {
    const [item] = runNode(workflow, 'Prepare email reply', [response], earlier);
    assert.equal(item.json.reply_body, 'Hello');
    assert.equal(item.json.reply_subject, 'Re: Question');
  }
  assert.throws(() => runNode(workflow, 'Prepare email reply', [{}], earlier), /empty email reply/);
});
