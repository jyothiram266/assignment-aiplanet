import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp-up to 5 VUs
    { duration: '1m',  target: 25 },  // Spike to 25 VUs to trigger KEDA autoscale
    { duration: '30s', target: 0 },   // Ramp-down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests should complete within 2s
  },
};

const TARGET_URL = __ENV.GATEWAY_URL || 'http://localhost:8000';

export default function () {
  const payload = JSON.stringify({
    messages: [
      { role: 'user', content: 'What is the return policy for electronic items?' }
    ],
    max_tokens: 50,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${TARGET_URL}/v1/chat/completions`, payload, params);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has choices': (r) => r.body && r.body.includes('choices'),
  });

  sleep(0.2); // 200ms delay between iterations
}
