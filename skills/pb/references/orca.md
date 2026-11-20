# PBL 내보내기 (ORCA)

동봉한 `scripts/Export-PBL.ps1`과 `scripts/PblExporter.exe`(x86 도우미)를 쓴다. 별도 PblScripter 설치는 필요 없지만, PowerBuilder ORCA 런타임(PB 7.0 / 10.5 / 12.5)은 이 PC에 설치되어 있어야 한다.

## 실행

출력 폴더는 소스 프로젝트 밖의 작업용 임시 폴더로 지정한다. 스킬 폴더 경로는 절대 경로로 쓴다.

```powershell
# 객체 목록 (목록은 콘솔에만 나오지만 -OutputDirectory가 없으면 종료 코드 17로 멈춘다)
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action list -OutputDirectory "<temp>\pbl-export"

# 전체 내보내기
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action exportall -OutputDirectory "<temp>\pbl-export"

# 객체 하나
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action export -ObjectName "d_employee" -OutputDirectory "<temp>\pbl-export"
```

- 버전을 모르면 `125` → `105` → `70` 순서로 `-Action list`부터 시도한다. 런타임이 표준 경로에 없으면 `-OrcaDllPath`, `-RuntimePath`로 지정한다. 실제로 PB 7 PBL은 `125`에서 SySAM 라이선스 오류, `105`에서 `Bad library`가 나고 `70`에서 목록이 나왔다. 이 두 오류는 다음 버전으로 넘어가라는 뜻이다.
- 목록이 나온 버전으로 필요한 객체만 `-Action export`로 꺼낸다. 화면 하나를 분석할 때는 윈도우(또는 사용자 객체)와 거기서 `dataobject`로 부르는 DataWindow만 꺼내면 된다.
- 이미 내보낸 파일이 있어도 어느 PBL에서 언제 내보냈는지 모르면, 같은 객체를 다시 내보내 비교한 뒤 근거로 쓴다. 같으면 기존 파일의 줄 번호를 그대로 쓴다.
- 내보내기는 PBL을 고치지 않지만, 원본 폴더 대신 사본 PBL이 있으면 사본에서 꺼낸다. 출력 폴더는 원본 폴더 밖이어야 한다.
- PBL 헤더가 0600이라고 PB 6으로 단정하지 않는다. 읽을 수 있는 런타임을 찾은 것이지 원래 작성 버전을 증명한 것이 아니다.

## 성공 판정

- 종료 코드 0이라도 `Session open failed`, `Bad library`, SySAM/라이선스 오류, 빈 출력이면 **실패**다.
- 종료 코드 0인데 새 출력 파일이 없으면 **미확인**이다.
- 실패하면 사용자가 준 내보내기 파일이나 붙여넣은 소스로 계속하고, 빠진 근거를 밝힌다.
- 분석만 하는 경우 필요한 소스를 읽은 뒤 임시 출력 폴더를 지운다. 최종 산출물로 요청받은 내보내기는 남긴다.
