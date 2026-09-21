// Decode n8n address objects and tolerate missing or invalid dates.
const extractEmail = (value) => {
  if (!value) return '';
  if (typeof value === 'object') {
    if (Array.isArray(value.value) && value.value[0]?.address) {
      return String(value.value[0].address).toLowerCase();
    }
    if (value.address) return String(value.address).toLowerCase();
    if (value.text) value = value.text;
  }

  const text = String(value);
  const bracketAddress = text.match(/<([^>]+)>/);
  const candidate = bracketAddress?.[1] ?? text;
  const match = candidate.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  return match ? match[0].toLowerCase() : '';
};

const formatAddress = (value) => {
  if (!value) return '';
  if (typeof value === 'object') {
    if (value.text) return String(value.text);
    if (Array.isArray(value.value)) {
      return value.value
        .map((entry) => entry?.address ? (entry.name ? entry.name + ' <' + entry.address + '>' : entry.address) : '')
        .filter(Boolean)
        .join(', ');
    }
    if (value.address) return value.name ? value.name + ' <' + value.address + '>' : String(value.address);
  }
  return String(value);
};

const parseDate = (value) => {
  const parsed = value ? new Date(value) : new Date();
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed;
};
