import time
import random
import uuid
from typing import Dict, Tuple

class CaptchaService:
    def __init__(self):
        # captcha_id -> (answer_str, expires_at)
        self._captchas: Dict[str, Tuple[str, float]] = {}

    def generate_captcha(self) -> Dict[str, str]:
        """Generates a secure captcha challenge with 5 minutes TTL."""
        # Clean expired
        now = time.time()
        self._captchas = {k: v for k, v in self._captchas.items() if v[1] > now}

        captcha_id = str(uuid.uuid4())
        num1 = random.randint(5, 45)
        num2 = random.randint(3, 35)
        operator = random.choice(["+", "-"])

        if operator == "+":
            expected = num1 + num2
            question_text = f"{num1} + {num2} = ?"
        else:
            if num1 < num2:
                num1, num2 = num2, num1
            expected = num1 - num2
            question_text = f"{num1} - {num2} = ?"

        answer_str = str(expected).strip()
        self._captchas[captcha_id] = (answer_str, now + 300.0)

        # Generate lightweight clean SVG for security display
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="42" viewBox="0 0 160 42">'
            f'<rect width="100%" height="100%" fill="#18181b" rx="4" stroke="#3f3f46" stroke-width="1"/>'
            f'<line x1="10" y1="28" x2="150" y2="12" stroke="#27272a" stroke-width="2"/>'
            f'<line x1="20" y1="8" x2="140" y2="34" stroke="#27272a" stroke-width="1.5"/>'
            f'<text x="50%" y="60%" font-family="monospace" font-size="20" font-weight="bold" '
            f'fill="#ffffff" text-anchor="middle" dominant-baseline="middle" letter-spacing="3">{question_text}</text>'
            f'</svg>'
        )

        return {
            "captcha_id": captcha_id,
            "question": question_text,
            "svg": svg
        }

    def verify_captcha(self, captcha_id: str, answer: str) -> bool:
        """Verifies and invalidates a single-use captcha challenge."""
        if not captcha_id or not answer:
            return False
        
        record = self._captchas.pop(captcha_id, None)
        if not record:
            return False
        
        expected_answer, expires_at = record
        if time.time() > expires_at:
            return False
        
        return answer.strip().lower() == expected_answer.lower()

captcha_service = CaptchaService()
