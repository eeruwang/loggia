You are running as an unattended task once a day at 07:30 KST. Model: claude-opus-5. Do the whole job in one pass, then stop.

로지아 판과 틱틱을 맞춘다. 판의 할 일과 마감을 틱틱으로 보내고, 틱틱에서 체크하거나 고친 것을 판의 장부로 돌려보낸다.

=== 꼭 지킬 것 ===

1. **판단은 도구가 한다.** 무엇을 만들고 지울지 `tools/ticktick-plan.py` 가 적어 준다. 계획을 눈으로 다시 고르지 마라
2. **장부에 넣지 못하면 틱틱을 건드리지 않는다.** POST 가 막히면 그 회차는 아무것도 지우거나 고치지 않고 멈춘다. 되받을 것을 잃는 쪽이 더 나쁘다
3. **`data.enc` 를 직접 고치지 않는다.** 장부에 넣으면 워커가 열 분 안에 옮긴다
4. **갈래를 바꾸지 않는다.** 사람이 어떤 줄을 노트로 바꿔 두었으면 그대로 둔다. 노트는 체크할 수 없고 하위로도 못 들어간다. 틱틱이 막는다
5. **마감 목록은 비추기만 한다.** 그 목록의 완료는 읽지 않는다. 날이 지난 마감은 계획이 알아서 뺀다
6. **틱틱 목록을 새로 만들지 않는다.** 아래 두 아이디를 쓴다

| 무엇 | 아이디 |
| --- | --- |
| 로지아 할 일 | `6aa7ae1d8f084b19082e331e` |
| 로지아 마감 | `6aa7ae1f8f081102b5324922` |

할 일 목록은 항목이 어버이 과제가 되고 할 일이 그 하위로 붙는다.
어버이 본문에는 `로지아 항목 <아이디>` 한 줄, 하위에는 `로지아 <아이디>.<지문여덟자>` 한 줄.
지문은 할 일 글의 sha1 앞 여덟 자다. 이 줄을 지우면 그 과제는 길을 잃는다.

**본문의 나머지는 사람의 자리다.** 그 아래로 메모를 적는다. 열쇠 줄은 첫 줄이 아니어도 되고,
계획 도구가 줄마다 훑어 찾는다. 열쇠를 갈아 끼울 때도 그 한 줄만 바꾸고 메모는 그대로 둔다.
**계획이 준 `content` 를 그대로 넘긴다.** 사람 메모를 살려 둘 책임은 계획 쪽에 있다.

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
`kind` 와 `parentId` 를 빠뜨리면 노트가 되받기로 흘러가고 하위가 다시 붙는다.

```json
{"todo": [{"id":"", "title":"", "content":"", "dueDate":"", "tags":[],
           "kind":"TEXT", "parentId":null, "status":0, "completedTime":null}],
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

**6. 틱틱을 맞춘다.** 장부가 받아졌을 때만 한다. 차례가 중요하다.

- `create_parent` 를 `batch_add_tasks` 로 먼저 만든다. 돌아온 아이디를 항목마다 적어 둔다
- `create_todo` 의 `parentKey` 가 방금 만든 어버이를 가리키면 그 아이디를 `parentId` 에 넣는다. `parentKey` 자리는 지우고 `batch_add_tasks` 로 넘긴다. 스무 개씩 끊는다
- `create_due` 를 `batch_add_tasks` 로 넘긴다
- `update` 를 `batch_update_tasks` 로 넘긴다
- `delete` 는 하나씩 `delete_task` 로 지운다

**7. 알린다.** 계획의 `report` 가 비었고 만들거나 지운 것도 없으면 아무 데도 적지 말고 끝낸다. 움직인 것이 있거나 5번에서 멈췄으면 Gmail 초안을 하나 만든다. 제목은 `로지아 틱틱 동기화 <날짜>`, 받는 이는 moon@ilsunmoon.com, 본문은 열 줄 안쪽으로. 보내지 않는다.

=== 알아 둘 것 ===

**틱틱에서 새로 적은 할 일은 어버이 아래 적으면 판으로 간다.** 어버이 밖에 적었으면 항목 이름이나 아이디를 태그로 달아야 한다. 둘 다 없으면 계획이 그냥 두고 `report` 에 적는다. 그 줄은 초안에 옮겨 적어 사람이 알게 한다.

**할 일의 제목이 곧 열쇠다.** 틱틱에서 글을 고치면 계획이 `/edit` 로 보내고 본문의 열쇠도 새로 박는다. 사람이 본문을 손대지 않게 한다.

**어버이를 체크하면 계획이 되돌린다.** 어버이는 항목이지 할 일이 아니다. 체크해도 하위는 완료되지 않는다.

**공고는 하루 두 번 도는 공고 루틴이 채운다.** 여기서 `jobs/` 나 공고 KV 에 쓰지 않는다. 읽기만 한다.
