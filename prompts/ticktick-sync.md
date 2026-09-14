You are running as an unattended task once a day at 07:30 KST. Model: claude-opus-5. Do the whole job in one pass, then stop.

로지아 판과 틱틱을 맞춘다. 판의 할 일과 마감을 틱틱으로 보내고, 틱틱에서 체크하거나 고친 것을 판의 장부로 돌려보낸다.

=== 꼭 지킬 것 ===

1. **판단은 도구가 한다.** 무엇을 만들고 지울지 `tools/ticktick-plan.py` 가 적어 준다. 계획을 눈으로 다시 고르지 마라
2. **장부에 넣지 못하면 틱틱을 건드리지 않는다.** POST 가 막히면 그 회차는 아무것도 지우거나 고치지 않고 멈춘다. 되받을 것을 잃는 쪽이 더 나쁘다
3. **`data.enc` 를 직접 고치지 않는다.** 장부에 넣으면 워커가 열 분 안에 옮긴다. 이 회차에서 판을 다시 받아 확인하려 들지 마라
4. **마감 목록은 비추기만 한다.** 그 목록의 완료는 읽지 않는다. 날이 지난 마감은 계획이 알아서 뺀다
5. **틱틱 목록을 새로 만들지 않는다.** 아래 두 아이디를 쓴다

| 무엇 | 아이디 |
| --- | --- |
| 로지아 할 일 | `6aa7ae1d8f084b19082e331e` |
| 로지아 마감 | `6aa7ae1f8f081102b5324922` |

=== 순서 ===

**1. 열쇠.** 드롭박스 `Moon Ilsun/01. Projects/00. Job Search/board_keys.txt` 에서 `PAGE_PASSPHRASE` 와 `LEDGER_TOKEN` 을 읽는다.

**2. 판을 받는다.**

```bash
curl -sO https://raw.githubusercontent.com/eeruwang/loggia/main/tools/fetch.sh
bash fetch.sh "<암호>" /tmp/lg && cd /tmp/lg
curl -s "https://loggia.moonilsun.com/gongo?k=<장부토큰>" > /tmp/gongo.json
```

**3. 틱틱의 지금을 받는다.** 세 번 부른다.

- `get_project_with_undone_tasks` 로 할 일 목록
- `list_completed_tasks_by_date` 로 할 일 목록의 지난 이레치 완료
- `get_project_with_undone_tasks` 로 마감 목록

받은 것을 `/tmp/current.json` 에 이렇게 적는다. 완료한 것은 `todo` 에 함께 담는다.

```json
{"todo": [{"id":"", "title":"", "content":"", "dueDate":"", "tags":[],
           "status":0, "completedTime":null}],
 "due":  [{"id":"", "title":"", "content":"", "dueDate":"", "tags":[]}]}
```

**4. 계획을 받는다.**

```bash
python3 tools/ticktick-plan.py --current /tmp/current.json --gongo /tmp/gongo.json > /tmp/plan.json
```

**5. 장부부터 보낸다.** 계획의 `ledger` 가 비어 있지 않은 칸만 보낸다.

```bash
curl -s -X POST "https://loggia.moonilsun.com/done?k=<장부토큰>" \
  -H 'content-type: application/json' -d '{"set": <ledger.done>}'
# /add 와 /edit 도 같은 꼴로
```

응답이 JSON 으로 돌아오지 않으면 거기서 멈춘다. 아래 6번을 하지 않는다. 무엇이 막혔는지 적어 알린다.

**6. 틱틱을 맞춘다.** 장부가 받아졌을 때만 한다.

- `batch_add_tasks` 에 `create_todo` 와 `create_due` 를 넘긴다. 스무 개씩 끊는다
- `batch_update_tasks` 에 `update` 를 넘긴다
- `delete` 는 하나씩 `delete_task` 로 지운다

**7. 알린다.** 계획의 `report` 가 비었고 만들거나 지운 것도 없으면 아무 데도 적지 말고 끝낸다. 움직인 것이 있거나 5번에서 멈췄으면 Gmail 초안을 하나 만든다. 제목은 `로지아 틱틱 동기화 <날짜>`, 받는 이는 moon@ilsunmoon.com, 본문은 열 줄 안쪽으로. 보내지 않는다.

=== 알아 둘 것 ===

**열쇠는 과제 본문 첫 줄에 산다.** 할 일은 `로지아 <항목아이디>.<지문여덟자>`, 마감은 `로지아 마감 item:<아이디>` 나 `venue:` 나 `repeat:` 나 `gongo:`. 지문은 할 일 글의 sha1 앞 여덟 자다. 이 줄을 지우면 그 과제는 길을 잃는다.

**틱틱에서 새로 적은 할 일은 항목 아이디를 태그로 달아야 판으로 간다.** 태그가 없으면 계획이 그냥 두고 `report` 에 적는다. 그 줄은 초안에 옮겨 적어 사람이 알게 한다.

**할 일의 제목이 곧 열쇠다.** 틱틱에서 글을 고치면 계획이 `/edit` 로 보내고 본문의 열쇠도 새로 박는다. 사람이 본문을 손대지 않게 한다.

**공고는 하루 두 번 도는 공고 루틴이 채운다.** 여기서 `jobs/` 나 공고 KV 에 쓰지 않는다. 읽기만 한다.
