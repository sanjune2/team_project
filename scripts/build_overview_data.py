"""기존 overview 명령의 호환 진입점. 생성 로직은 analysis.overview_runner를 공유한다."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis.overview_runner import generate, main, run_batch, save

if __name__ == '__main__':
    raise SystemExit(main())
