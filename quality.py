import re
from pathlib import Path

OUTPUT_DIR = Path("output")


def check_vocabulary_diversity(conversations: list[dict]) -> dict:
    all_words = []
    for c in conversations:
        for msg in c.get("user_messages", []):
            words = re.findall(r"\w+", msg.lower())
            all_words.extend(words)

    if not all_words:
        return {"pass": False, "ttr": 0, "total": 0, "unique": 0}

    total = len(all_words)
    unique = len(set(all_words))
    ttr = unique / total if total > 0 else 0

    return {
        "pass": ttr > 0.35,
        "ttr": round(ttr, 3),
        "total": total,
        "unique": unique,
    }


def check_sentence_starters(conversations: list[dict]) -> dict:
    banned = {"can you", "this is", "i'm trying to", "i want", "i need", "could you"}
    bad_count = 0
    total = 0
    starter_counts = {}

    for c in conversations:
        for msg in c.get("user_messages", []):
            msg = msg.strip().lower()
            if not msg:
                continue
            total += 1
            first_three = " ".join(msg.split()[:3])
            first_word = msg.split()[0] if msg.split() else ""
            starter_counts[first_three] = starter_counts.get(first_three, 0) + 1

            for b in banned:
                if msg.startswith(b):
                    bad_count += 1
                    break

    return {
        "pass": bad_count < total * 0.15 if total > 0 else True,
        "bad_starter_pct": round(bad_count / total * 100, 1) if total > 0 else 0,
        "top_starters": dict(sorted(starter_counts.items(), key=lambda x: -x[1])[:5]),
    }


def check_all_caps_presence(conversations: list[dict]) -> dict:
    caps_count = 0
    for c in conversations:
        for msg in c.get("user_messages", []):
            words = msg.split()
            caps_words = [w for w in words if w.isupper() and len(w) > 2]
            if caps_words:
                caps_count += 1
                break

    return {
        "pass": caps_count >= len(conversations) * 0.1,
        "conversations_with_caps": caps_count,
        "pct": round(caps_count / len(conversations) * 100, 1) if conversations else 0,
    }


def check_message_length_variety(conversations: list[dict]) -> dict:
    lengths = [len(c.get("user_messages", [])) for c in conversations]
    if not lengths:
        return {"pass": False, "min": 0, "max": 0, "stdev": 0}

    avg = sum(lengths) / len(lengths)
    variance = sum((x - avg) ** 2 for x in lengths) / len(lengths)
    stdev = variance ** 0.5

    return {
        "pass": stdev > 1.5 and min(lengths) >= 1,
        "min": min(lengths),
        "max": max(lengths),
        "stdev": round(stdev, 2),
    }


def check_politeness(conversations: list[dict]) -> dict:
    polite_phrases = ["please", "thank you", "kindly", "would you mind", "i apologize", "sorry for"]
    polite_count = 0
    total_messages = 0

    for c in conversations:
        for msg in c.get("user_messages", []):
            total_messages += 1
            msg_lower = msg.lower()
            if any(p in msg_lower for p in polite_phrases):
                polite_count += 1

    return {
        "pass": polite_count < total_messages * 0.2 if total_messages > 0 else True,
        "polite_pct": round(polite_count / total_messages * 100, 1) if total_messages > 0 else 0,
    }


def check_financial_specifics(conversations: list[dict], domain_type: str = "") -> dict:
    patterns = [r"₹\d+", r"rs\s*\d+", r"\d+\s*(lakh|crore|k|thousand)", r"(order|ref|txn|id)\s*[#:]\s*\w+"]
    found = 0
    for c in conversations:
        for msg in c.get("user_messages", []):
            if any(re.search(p, msg, re.IGNORECASE) for p in patterns):
                found += 1
                break

    return {
        "pass": found >= len(conversations) * 0.15,
        "conversations_with_specifics": found,
        "pct": round(found / len(conversations) * 100, 1) if conversations else 0,
    }


def check_no_llm_patterns(conversations: list[dict]) -> dict:
    patterns = [
        r"your competitor.*\w+",
        r"\w+ \(a \w+ company\)",
        r"i understand.*frustrat",
        r"let me.*help",
        r"i'm sorry to hear",
    ]
    found = 0
    for c in conversations:
        for msg in c.get("user_messages", []):
            if any(re.search(p, msg, re.IGNORECASE) for p in patterns):
                found += 1
                break

    return {
        "pass": found < len(conversations) * 0.05,
        "llm_pattern_count": found,
    }


def run_all_checks(conversations: list[dict], domain_type: str = "") -> dict:
    checks = {
        "vocabulary_diversity": check_vocabulary_diversity(conversations),
        "sentence_starters": check_sentence_starters(conversations),
        "all_caps_presence": check_all_caps_presence(conversations),
        "message_length_variety": check_message_length_variety(conversations),
        "politeness": check_politeness(conversations),
        "financial_specifics": check_financial_specifics(conversations, domain_type),
        "no_llm_patterns": check_no_llm_patterns(conversations),
    }

    passed = sum(1 for c in checks.values() if c["pass"])
    total = len(checks)

    return {
        "overall": {
            "pass": passed == total,
            "passed": passed,
            "total": total,
            "score": round(passed / total * 100, 1),
        },
        "checks": checks,
    }


def print_report(report: dict) -> None:
    print("\n" + "=" * 50)
    print("QUALITY REPORT")
    print("=" * 50)

    status = "PASS" if report["overall"]["pass"] else "FAIL"
    print(f"[{status}] Score: {report['overall']['score']}% ({report['overall']['passed']}/{report['overall']['total']} checks passed)")

    for name, check in report["checks"].items():
        icon = "[PASS]" if check["pass"] else "[FAIL]"
        print(f"  {icon} {name.replace('_', ' ').title()}")

        details = {k: v for k, v in check.items() if k != "pass"}
        for k, v in details.items():
            print(f"      {k}: {v}")

    print("=" * 50)
