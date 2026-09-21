// The legacy SQL nodes sometimes return JSON text instead of an object.
// Example: email = parsePayload(row.email_payload);
const parsePayload = (value) => {
  if (!value) return {};
  if (typeof value === 'string') return JSON.parse(value);
  return value;
};

// Example: item = payloadItem(email);
function payloadItem(emailPayload) {
  return {
    json: {
      ...emailPayload,
      email_payload: emailPayload,
      email_payload_sql: JSON.stringify(emailPayload).replace(/'/g, "''"),
    },
  };
}
