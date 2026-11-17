# 지상행 · Subway Escape

macOS에서 실행하는 240×240 지하철 탈출 게임입니다. B2에서 출발해 B1과 1F를 거쳐, 1F의 EXIT에서 B를 누르면 탈출합니다.

## macOS 실행

Tk를 지원하는 Python 3.10 이상을 사용합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## 조작

| 키 | 플레이 | 메뉴 |
| --- | --- | --- |
| ← / → | 좌우로 이동 | 상황·난이도 선택 |
| ↑ / ↓ | | 항목 또는 시설 방향 선택 |
| A / Space | 점프 | 선택·확정 |
| Enter | | 선택·확정 |
| B / Esc | 가까운 시설 이용 | 취소·뒤로 |

유모차와 다리 불편 상황은 엘리베이터로 이동합니다. 화장실 상황은 B1의 WC를 방문해야 합니다. NORMAL과 HARD에서는 B2의 첫 엘리베이터가 고장 나 있으며, 오른쪽의 대체 엘리베이터를 이용할 수 있습니다.

## 파일

- `main.py` · tkinter 창과 프레임 루프
- `buttons.py` · 버튼 상태와 키보드 어댑터
- `game.py` · 상태 전환, 물리, 시설 및 충돌 판정
- `display.py` · 240×240 Pillow 렌더러
- `config.py` / `levels.py` · 상황 및 난이도, 층별 맵 데이터

```sh
python -m unittest discover -s tests
```

## Raspberry Pi 5 / ST7789

`pi_main.py`는 배선이 정해지면 사용할 LCD/GPIO 어댑터입니다. macOS 실행에는 Pillow만 필요합니다. Pi에서는 SPI를 활성화하고 `adafruit-blinka`와 `adafruit-circuitpython-rgb-display`를 설치합니다.

실행 전에 LCD의 전원·접지, SPI SCLK/MOSI, CS/DC/RST, 백라이트 배선과 버튼 6개의 GPIO 및 공통 접지를 확인합니다. 어댑터는 Blinka의 기본 SPI 버스와 GND로 닫히는 내부 풀업 버튼을 사용합니다. LCD의 표시 방향과 X/Y 오프셋은 모듈에 맞춰 전달합니다.

```sh
python pi_main.py --help
```

실제 배선과 LCD 모듈에서의 동작 확인이 필요합니다.
# KAU-2026-02-ESW-SubwayEscape
