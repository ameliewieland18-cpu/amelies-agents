// Convert an incoming message, skip our own mail, and pass on a database payload.
const email = normalizeEmail($json);
return email ? [payloadItem(email)] : [];
