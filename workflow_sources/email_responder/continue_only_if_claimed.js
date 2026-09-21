// Only the worker that owns the new database claim may continue.
if (!$json.should_reply) {
  return [];
}

const emailPayload = parsePayload($json.email_payload);
emailPayload.top_k = Number($json.top_k ?? emailPayload.top_k ?? 5);
emailPayload.email_record_id = $json.email_record_id;

return [{
  json: {
    ...emailPayload,
    email_payload: emailPayload,
    email_payload_sql: JSON.stringify(emailPayload).replace(/'/g, "''"),
    top_k: emailPayload.top_k,
    email_record_id: $json.email_record_id,
  },
}];
