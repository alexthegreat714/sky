echo [2] RAG — write/search/count (Sky namespace)
REM Use PowerShell to emit real JSON; avoids CMD escaping hell.

REM -- write --
%PS% ^
  "$b = @{ text = 'Night Agent schedule: 23:30-03:00 build+tests.'; source='ops'; kind='schedule'; priority=0.9 } | ConvertTo-Json -Compress; " ^
  "Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:%PORT%/rag/write' -ContentType 'application/json' -Body $b | ConvertTo-Json -Depth 6"

echo.
REM -- search --
%PS% ^
  "$b = @{ query = 'tonight plan'; top_k = 3; min_priority = 0.8 } | ConvertTo-Json -Compress; " ^
  "Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:%PORT%/rag/search' -ContentType 'application/json' -Body $b | ConvertTo-Json -Depth 6"

echo.
REM -- count (POST with filters) --
%PS% ^
  "$b = @{ where = @{ source = 'ops' } } | ConvertTo-Json -Compress; " ^
  "Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:%PORT%/rag/count' -ContentType 'application/json' -Body $b | ConvertTo-Json -Depth 6"

echo.
REM -- list (GET, no filters) --
"%CURL%" -s "http://127.0.0.1:%PORT%/rag/list?limit=5&offset=0" & echo.
echo ----------------------------------------------------------
