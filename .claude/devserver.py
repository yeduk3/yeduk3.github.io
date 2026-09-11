"""개발용 정적 서버. python -m http.server는 Cache-Control을 안 보내서
브라우저가 휴리스틱 캐싱으로 옛 CSS를 재사용한다. no-store로 막는다.
운영(GitHub Pages)은 ETag를 보내므로 이 문제가 없다."""
import http.server

class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

if __name__ == "__main__":
    http.server.test(HandlerClass=NoCache, port=4173, bind="127.0.0.1")
