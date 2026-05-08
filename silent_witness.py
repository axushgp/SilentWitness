from __future__ import annotations

from dataclasses import asdict, dataclass, field

from alerter import compose_alert, send_telegram
from classifier import classify
from crawler import crawl
from differ import diff_all
from dpdp_checker import check as check_dpdp
from mike_bridge import analyze_policy
from risk_scorer import score
from vault import add_change, finish_run, init_db, start_run


@dataclass
class ServiceRun:
    service: str
    status: str
    severity: str | None = None
    risk_score: int | None = None
    change_id: int | None = None
    alert_sent: bool = False
    classifier: str | None = None
    mike_source: str | None = None
    report_path: str | None = None
    error: str | None = None


@dataclass
class HeartbeatResult:
    run_id: int
    crawled: int
    failed: int
    diffs: int
    alerts: int
    services: list[ServiceRun] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "crawled": self.crawled,
            "failed": self.failed,
            "diffs": self.diffs,
            "alerts": self.alerts,
            "services": [asdict(item) for item in self.services],
        }


def run_heartbeat(send_alerts: bool = True) -> HeartbeatResult:
    init_db()
    run_id = start_run()
    print("Silent Witness heartbeat starting...")

    crawl_results = crawl()
    crawled = sum(1 for item in crawl_results if item.status == "crawled")
    failed = len(crawl_results) - crawled
    print(f"Crawler: {crawled} crawled, {failed} failed")
    if failed:
        print("Crawler fallback: using existing local snapshots where available")

    diffs = diff_all()
    found = 0
    alerts = 0
    service_runs: list[ServiceRun] = []
    for diff in diffs:
        if diff.status != "diff_found":
            print(f"{diff.service}: {diff.status}")
            service_runs.append(ServiceRun(diff.service, diff.status))
            continue

        found += 1
        classification = classify(diff.diff_text)
        risk = score(diff.diff_text, classification.severity)
        dpdp_flags = check_dpdp(diff.diff_text)
        mike_result = None
        if classification.severity == "CRITICAL":
            mike_result = analyze_policy(diff.service, diff.current_path, diff.diff_text)
        change_id = add_change(
            diff.service,
            classification.severity,
            classification.summary,
            classification.deadline,
            risk,
            dpdp_flags,
            diff.diff_text,
            mike_result.report_path if mike_result else None,
            mike_result.clauses if mike_result else [],
        )
        print(
            f"{diff.service}: {classification.severity}, "
            f"risk {risk.total_score}/100, stored change #{change_id}"
        )

        alert_sent = False
        if send_alerts and classification.severity in {"CRITICAL", "MODERATE"}:
            message = compose_alert(
                diff.service,
                classification,
                risk,
                dpdp_flags,
                diff.diff_text,
                mike_result.report_path if mike_result else None,
            )
            try:
                alert_sent = send_telegram(message)
            except OSError as exc:
                alert_sent = False
                print(f"{diff.service}: Telegram send failed: {exc}")
            if alert_sent:
                alerts += 1
            else:
                print(f"{diff.service}: Telegram not sent (token/chat missing or request failed)")
        service_runs.append(
            ServiceRun(
                service=diff.service,
                status=diff.status,
                severity=classification.severity,
                risk_score=risk.total_score,
                change_id=change_id,
                alert_sent=alert_sent,
                classifier=classification.source,
                mike_source=mike_result.source if mike_result else None,
                report_path=mike_result.report_path if mike_result else None,
                error=mike_result.error if mike_result else None,
            )
        )

    result = HeartbeatResult(run_id, crawled, failed, found, alerts, service_runs)
    finish_run(run_id, crawled, failed, found, alerts, "complete", result.to_dict())
    print(f"Heartbeat complete: {found} meaningful diffs, {alerts} Telegram alerts sent")
    return result


if __name__ == "__main__":
    run_heartbeat()
