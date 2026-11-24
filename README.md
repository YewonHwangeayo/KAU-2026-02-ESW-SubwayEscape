# 지상행 · Subway Escape

지하철역 B2에서 출발해 B1을 거쳐 지상 1F 출구에 도착하는 240×240 횡스크롤 게임입니다.

## 1. 배경 및 아이디어

같은 지하철역에서도 캐리어를 끌거나 유모차를 밀 때, 또는 화장실을 먼저 찾아야 할 때 적합한 경로는 달라집니다. 이 차이를 게임에 반영해 같은 역을 탐색하더라도 선택한 상황에 따라 이용할 시설과 목표가 달라지도록 만들었습니다. 플레이어는 남은 시간과 체력을 보면서 계단, 에스컬레이터, 엘리베이터 중 자신의 상황에 맞는 경로를 고릅니다.

## 2. 게임 방법

### 조작 방법

| 키보드 | 물리 버튼 | 플레이 중 | 메뉴 및 시설 선택 |
| --- | --- | --- | --- |
| ← / → | LEFT / RIGHT | 누르는 동안 좌우 이동 | 상황·난이도 선택 |
| ↑ / ↓ | UP / DOWN | — | 항목 이동 및 UP/DOWN 선택 |
| A / Space | A | 점프 | 선택 및 확정 |
| Enter | — | — | 선택 및 확정 |
| B / Esc | B | 가까운 시설 이용 | 취소 및 뒤로 가기 |

### 게임 규칙

1. 타이틀에서 시작한 뒤 상황과 난이도를 고릅니다.
2. 시설 가까이에서 B를 누릅니다. 계단·에스컬레이터·엘리베이터는 UP 또는 DOWN을 고른 후 A로 확정합니다. UP은 위층으로 이동하고, DOWN을 확정하면 게임이 종료됩니다.
3. B2 → B1 → 1F 순서로 이동한 뒤 1F의 EXIT에서 B를 누르면 `GAME CLEAR`가 됩니다. 시간이나 체력이 0이 되면 `GAME OVER`가 됩니다.

| 상황 | 시설 및 목표 |
| --- | --- |
| 일반 | 계단, 상행 에스컬레이터, 엘리베이터를 이용해 탈출 |
| 캐리어 | 계단 이용 시 체력 30 감소. 에스컬레이터 이용 시 게임 종료 |
| 유모차 | 엘리베이터만 이용 가능. 전 층에서 가시 비활성화 |
| 노인 | 계단 이용 시 체력 30, 에스컬레이터 이용 시 체력 5 감소 |
| 다리 불편 | 엘리베이터만 이용 가능. 전 층에서 가시 비활성화 |
| 화장실 급함 | 1F에서 나가기 전에 B1의 WC에서 B를 눌러 방문. 방문 후에도 남은 시간 유지 |

- 시작 체력은 100입니다. 가시에 닿으면 5초 동안 남은 시간이 평소의 2배 속도로 줄어듭니다. 점프로 넘을 수 있습니다.
- NORMAL과 HARD에서는 B2의 첫 엘리베이터가 고장 나 있습니다. 더 오른쪽에 이용할 수 있는 엘리베이터가 있습니다.
- B1의 `WRONG EXIT`를 이용하면 해당 층의 시작점으로 돌아갑니다. 캐리어와 노인 상황에서는 체력이 10 줄어듭니다.

## 3. 사용 기술

### 하드웨어

| 장치 | 역할 |
| --- | --- |
| Mac과 키보드 | 게임 개발 및 시뮬레이터 실행 |
| Raspberry Pi 5 | LCD 출력과 버튼 입력을 처리할 실행 장치 |
| ST7789 240×240 SPI LCD | 게임 프레임 표시 |
| 순간 누름 버튼 6개 | 방향키 4개와 A·B 입력을 GPIO로 전달 |

### 소프트웨어

Python 3.10 이상으로 게임을 작성했습니다. macOS에서는 tkinter로 창과 키 입력을 처리하고, Pillow로 240×240 이미지를 그립니다. Raspberry Pi용 어댑터에서는 Adafruit Blinka로 SPI·GPIO에 접근하고 Adafruit RGB Display 라이브러리로 LCD에 프레임을 전송합니다.

macOS에서 Tk를 지원하는 Python을 사용해 프로젝트 폴더에서 실행합니다.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Pi 실습 보드의 ST7789 LCD와 GPIO 버튼 실행은 다음과 같습니다.

```sh
source .venv_pi/bin/activate
python -m pip install -r requirements-pi.txt
python pi_main.py
```

기본 설정은 교수님이 제공한 `Joystick.py`에 맞춰 240×240, rotation 180, X offset 0, Y offset 80, 24MHz입니다. LCD CS는 CE0(GPIO8), DC는 D25, RESET은 D24, 백라이트는 D26입니다. 방향 버튼은 LEFT D27, RIGHT D23, UP D17, DOWN D22이며 A D5, B D6, C D4를 사용합니다. C는 입력 검사에만 사용합니다. 버튼은 참고 코드와 같이 입력 모드로 설정하며 눌렀을 때 LOW로 읽습니다.

CE0는 `/dev/spidev0.0`의 커널 하드웨어 CS로 제어합니다. GPIO8을 `DigitalInOut`으로 요청하지 않으며 Adafruit LCD 드라이버에는 `cs=None`을 전달합니다. SPI0가 GPIO8을 CE0로 사용하도록 설정되어 있어야 합니다. 이전에 CE0를 다른 핀으로 재할당했다면 실제 SPI 설정을 확인해야 합니다.

```sh
python pi_main.py --mode diagnose
python pi_main.py --mode lcd-test --seconds 10
python pi_main.py --mode buttons-test --seconds 20
```

진단은 GPIO 점유 정보, GPIO8 핀 기능, SPI 사용 프로세스와 설정을 읽습니다. LCD 테스트는 RGB 색상과 흰 테두리를 출력하고, 버튼 테스트는 A/B/C 및 방향 버튼 상태를 터미널에 표시합니다. 종료는 Ctrl-C이며 SIGTERM도 정리 경로를 실행합니다. 이미 확보한 GPIO와 SPI는 초기화 오류 및 실행 예외에서도 해제하고 백라이트를 끕니다. 강제 종료 SIGKILL이나 전원 차단에서는 Python 정리 코드를 실행할 수 없습니다.

실제 GPIO 점유 원인과 LCD 출력, 버튼 입력, 종료 후 재실행은 Pi에서 확인해야 합니다. 개발 환경에서의 SSH 접속은 인증 실패로 완료하지 못했습니다.

## 4. 주요 기능 및 구현

### 게임 엔진 구조

프레임마다 입력 어댑터가 눌러 둔 버튼과 이번 프레임에 새로 누른 버튼을 `InputState`로 전달합니다. `Game.update(dt, input_state)`는 경과 시간과 입력으로 게임 상태를 갱신합니다. `render(game)`은 갱신된 상태를 읽어 Pillow 이미지를 만들고, 실행 진입점은 그 이미지를 Tk 창 또는 LCD로 전달합니다.

게임은 타이틀, 상황 선택, 난이도 선택, 목표 안내, 플레이, 시설 선택, 결과를 상태로 관리합니다. 좌우 이동에는 누르고 있는 상태를 사용하고 점프와 시설 선택에는 새로 누른 이벤트를 사용합니다. 타이머는 플레이 상태에서만 흐릅니다.

### 핵심 구현 사항

- **횡스크롤과 카메라** · B2와 B1은 폭 960px, 1F는 폭 480px입니다. 캐릭터의 월드 좌표를 기준으로 카메라가 따라가며, 맵 양끝에서는 화면 범위를 고정합니다.
- **점프와 충돌** · 중력으로 점프 궤적을 계산하고 바닥에 착지시키며, 캐릭터와 가시의 사각형 충돌 범위가 겹치는지 판정합니다.
- **상황별 장애물** · 유모차와 다리 불편에서는 층별 가시 목록을 비웁니다. 렌더러와 충돌 검사 모두 이 목록을 사용합니다.
- **시설과 HUD** · 시설 사용 시 연결된 층과 도착 좌표를 적용합니다. 상단 HUD에는 하트 5개, 현재 층, 남은 시간, 가시 페널티가 적용 중일 때의 `x2` 표시가 나옵니다.

## 5. 문제점과 해결책

### 난이도에 따라 다른 시간 배분

제한 시간이 한 가지로 정해져 있으면 처음 플레이하는 사람과 경로를 이미 익힌 사람에게 같은 시간 압박이 주어집니다. `config.py`에 세 난이도의 시작 시간을 정의했고, WC 방문이 필수인 화장실 급함 상황은 별도의 시간 값을 사용합니다.

| 난이도 | 일반 시간 | 화장실 급함 |
| --- | --- | --- |
| EASY | 150초 | 90초 |
| NORMAL | 120초 | 60초 |
| HARD | 90초 | 45초 |

### 가시 위에 서 있을 때 페널티가 계속 갱신되는 문제

매 프레임 겹침만 검사해 페널티를 적용하면 가시 위에 서 있는 동안 5초가 계속 갱신됩니다. 이를 막기 위해 현재 겹친 가시 목록을 직전 목록과 비교하고, 새로 접촉한 순간에만 발동 여부를 검사합니다. 발동 뒤 1초 동안은 재발동을 막습니다. 그 이후 다른 가시에 새로 닿으면 남은 페널티를 5초로 갱신하며, 차감 배율은 2배로 유지합니다.

## 6. 코드 구조 설명

### 프로젝트 구조

```text
subway_escape/
├── main.py              # macOS Tk 창 및 프레임 루프
├── pi_main.py           # Raspberry Pi LCD 및 GPIO 어댑터
├── buttons.py           # 공통 입력 상태 및 키보드 이벤트 처리
├── game.py              # 상태 전환, 물리, 충돌, 시설 규칙
├── display.py           # Pillow 화면 렌더러
├── config.py            # 화면, 물리, 상황, 난이도 설정
├── levels.py            # 층별 맵 크기, 시설, 도착 좌표, 가시 위치
├── requirements.txt    # Pillow 의존성
├── tests/
│   └── test_rules.py    # 메뉴, 완주 경로, 충돌, 타이머, 렌더링 검증
└── README.md
```

### 사용된 라이브러리

| 라이브러리·모듈 | 프로젝트에서의 사용 |
| --- | --- |
| `tkinter` | `Tk`로 창을 만들고, `bind`로 키 입력을 받으며, `after`로 다음 프레임을 예약 |
| `Pillow` | `Image`로 RGB 프레임 생성, `ImageDraw`로 지형과 HUD 그리기, `ImageFont`로 글꼴 설정, `ImageTk`로 Tk에 표시할 이미지 변환 |
| `time.monotonic` | 시스템 시각 변경의 영향을 받지 않는 프레임 간 경과 시간 계산 |
| `dataclasses` / `enum` | 입력·상황·시설 설정을 데이터 클래스로 정의하고, 게임 상태를 열거형으로 관리 |
| `Adafruit Blinka` | `board.SPI()`로 기본 SPI 버스를 열고, `digitalio`로 버튼 입력과 LCD 제어 핀 설정 |
| `adafruit_rgb_display.st7789` | LCD 크기와 오프셋 등을 설정하고, `lcd.image(...)`로 Pillow 프레임 전송 |
| `unittest` | 실행 창 없이 게임 규칙과 렌더링 결과를 자동 검증 |

### 라이브러리 활용 예시

macOS 프레임 루프에서는 `monotonic()`으로 구한 경과 시간을 게임에 전달하고, Pillow 렌더러가 만든 이미지를 `ImageTk.PhotoImage`로 변환합니다. 아래는 `main.py`의 프레임 갱신 부분입니다.

```python
now = monotonic()
game.update(now - previous, keyboard.snapshot())
previous = now
photo = ImageTk.PhotoImage(render(game), master=root)
label.configure(image=photo)
label.image = photo
root.after(33, update_screen)
```

Raspberry Pi에서는 같은 Pillow 프레임을 LCD로 전송합니다. 아래는 `pi_main.py`에서 사용하는 GPIO 입력 설정과 화면 출력입니다.

```python
gpio[button].switch_to_input(pull=digitalio.Pull.UP)
lcd.image(render(game))
```

자동 테스트는 다음 명령으로 실행합니다.

```sh
python -m unittest discover -s tests
```
