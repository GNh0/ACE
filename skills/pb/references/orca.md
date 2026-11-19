# PBL 내보내기 (ORCA)

동봉한 `scripts/Export-PBL.ps1`과 `scripts/PblExporter.exe`(x86 도우미)를 쓴다. 별도 PblScripter 설치는 필요 없지만, PowerBuilder ORCA 런타임(PB 7.0 / 10.5 / 12.5)은 이 PC에 설치되어 있어야 한다.

## 실행

출력 폴더는 소스 프로젝트 밖의 작업용 임시 폴더로 지정한다. 스킬 폴더 경로는 절대 경로로 쓴다.

```powershell
# 객체 목록
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action list

# 전체 내보내기
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action exportall -OutputDirectory "<temp>\pbl-export"

# 객체 하나
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action export -ObjectName "d_employee" -OutputDirectory "<temp>\pbl-export"
```

- 버전을 모르면 `125` → `105` → `70` 순서로 시도한다. 런타임이 표준 경로에 없으면 `-OrcaDllPath`, `-RuntimePath`로 지정한다.
- PBL 헤더가 0600이라고 PB 6으로 단정하지 않는다. 읽을 수 있는 런타임을 찾은 것이지 원래 작성 버전을 증명한 것이 아니다.

## 성공 판정

- 종료 코드 0이라도 `Session open failed`, `Bad library`, SySAM/라이선스 오류, 빈 출력이면 **실패**다.
- 종료 코드 0인데 새 출력 파일이 없으면 **미확인**이다.
- 실패하면 사용자가 준 내보내기 파일이나 붙여넣은 소스로 계속하고, 빠진 근거를 밝힌다.
- 분석만 하는 경우 필요한 소스를 읽은 뒤 임시 출력 폴더를 지운다. 최종 산출물로 요청받은 내보내기는 남긴다.
