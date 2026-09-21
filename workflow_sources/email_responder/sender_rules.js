// The legacy workflow sender policy. Python settings are in .env instead.
const ACCOUNT_EMAIL = 'hello.wieland.collective@gmail.com';
const BLOCKED_SENDER_DOMAINS = [
  'freelancer.nl',
  'freelancer.com',
  'makro.nl',
  'makromarket.nl',
  'makro.market',
  'makro-market.nl',
];
const BLOCKED_SENDER_KEYWORDS = [
  'freelancer.nl',
  'makro market',
  'makromarket',
  'makro-market',
];

const domainMatches = (domain, blockedDomain) => domain === blockedDomain || domain.endsWith('.' + blockedDomain);

const getBlockedSenderReason = (senderEmail, senderRaw) => {
  const senderDomain = senderEmail.split('@').pop() || '';
  const blockedDomain = BLOCKED_SENDER_DOMAINS.find((domain) => domainMatches(senderDomain, domain));
  if (blockedDomain) {
    return {
      skip_reason: 'blocked_sender',
      skip_detail: 'sender domain matches ' + blockedDomain,
      blocked_sender_domain: blockedDomain,
    };
  }

  const senderText = normalizeWhitespace(senderRaw).toLowerCase();
  const blockedKeyword = BLOCKED_SENDER_KEYWORDS.find((keyword) => senderText.includes(keyword));
  if (blockedKeyword) {
    return {
      skip_reason: 'blocked_sender',
      skip_detail: 'sender name matches ' + blockedKeyword,
      blocked_sender_keyword: blockedKeyword,
    };
  }

  return {};
};
