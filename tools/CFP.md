# 지면을 판으로 보내기

`Daily opportunities digest` 루틴에 붙일 대목이다. 그 루틴이 이미 저널과
특집을 훑으므로 사이트를 새로 도는 손을 만들지 않는다. 찾은 것을 파일 하나에
더 적는 일만 붙인다.

채용 루틴은 `jobs/latest.json` 을 쓴다. 지면은 `jobs/cfp.json` 을 쓴다.
**두 파일을 섞지 않는다.** 한 파일을 같이 쓰면 뒤에 도는 쪽이 앞의 것을 덮는다.

`jobs/` 는 루틴의 자리다. 세션에서 손대지 않고 `publish.sh` 도 옮기지 않는다.
그래서 이 안내가 `tools/` 에 있다.

---

## 아래를 digest 프롬프트의 「판에 보내기」 자리에 붙인다

GitHub 커넥터로 저장소 `eeruwang/loggia` 의 `jobs/cfp.json` 을 그 회차의
지면 결과로 덮어쓴다. 새 파일을 만들지 말고 늘 이 한 자리를 쓴다. 채용 루틴이
쓰는 `jobs/latest.json` 은 건드리지 않는다. 워커가 열 분마다 걷어 판으로 옮긴다.

```json
{"set": {
  "<id>": {
    "id": "<id>",
    "strand": "지면",
    "region": "국제",
    "title": "지면 이름, 특집 제목",
    "url": "공고 주소",
    "posted": "YYYY-MM-DD",
    "deadline": "YYYY-MM-DD",
    "note": "분량과 주제, 확인한 것과 확인 못한 것",
    "venue": "<낼 곳 id 또는 빈 문자열>"
  }
}}
```

`strand` 는 반드시 `지면` 이다. 이 값으로 판의 「지면과 특집」 칸에 선다.
`id` 는 지면 약칭과 연도와 회차로 짓는다. 같은 `id` 면 판에서 덮어쓴다.
이번 회차에 건진 것이 없으면 `{"set": {}}` 를 쓴다.

**마감이 없으면 싣지 않는다.** 지면 마감은 날짜가 없으면 판에서 아무 일도
하지 못한다. 원문을 못 열었으면 `note` 에 그렇게 적되 날짜를 짐작으로
채우지 않는다.

`venue` 가 이 대목의 핵심이다. **아래 목록에 있는 곳이면 그 id를 적는다.**
그러면 담아두기를 눌렀을 때 새 카드가 서지 않고 그 낼 곳의 마감만 갈아
끼워진다. 같은 마감이 두 자리에 생기지 않는다. 목록에 없는 곳이면 빈
문자열로 둔다. 사람이 낼 곳으로 만들지 정한다.

```
actakoreana advancehe aesthetics angelaki arko bja camobs capacious dgs
filmcomment filmphil fss glasgow greyroom humanities iaac ifm ijfma inmun
jaac jac jcms jvc koreajournal kosma leonardo liverpool macdowell mfj miraj
necsus newnham ngc nrfts oaj october opencity orgsound refocus scms screen
senses sophia tcs yonsei
```

무엇을 줍는지는 그 루틴이 이미 쓰고 있는 기준을 따른다. 분위기, 일기적
무빙이미지, 영화철학, 미학, 매체예술. 마감이 지난 것은 뺀다.

---

## 판에서 무슨 일이 일어나나

공고 판의 「지면과 특집」 칸에 선다. 담아두기를 누르면 씨앗이 남고, 다음
갱신에 이렇게 갈린다.

- `venue` 가 적힌 것 → 그 낼 곳의 마감이 바뀐다
- `venue` 가 빈 것 → 낼 곳으로 새로 만들지 사람에게 묻는다

월요일 아침 편지에 「지면 마감」 칸이 붙는다. 예순 날 안으로 들어온 것
가운데 넷까지 보여준다. 다른 요일에는 붙지 않으므로, 날마다 써 넣어도
소음이 되지 않는다.

## 채용 루틴에도 한 줄

`jobs/latest.json` 을 쓰는 채용 루틴의 json 예시 아래에 이 한 줄을 넣는다.

> `strand` 는 `연구소` 아니면 `강의` 둘 중 하나다. 다른 말을 쓰지 않는다.

예시에 `연구소` 만 있고 영국 강의직을 무엇으로 적을지 없어서, 회차마다
영국강의직과 영국강의와 영국과 강의가 섞여 들어왔다. 판은 두 값만 그려서
75건 가운데 60건이 안 보였다. 워커에 갈래를 맞추는 손을 붙여 지금은 무엇이
들어와도 둘로 모이지만, 루틴 쪽에서 못 박아 두는 편이 낫다.
