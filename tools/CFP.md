# 지면을 판으로 보내기

주 한 번 도는 **「매주 논문 받기」**(필름 필로소피 다이제스트) 루틴에 붙일 대목이다.
그 루틴의 Part B 가 이미 PhilEvents, H-Net, UPenn, ArtHist, e-flux,
MDPI Humanities, Intellect 일곱 길목을 훑는다. 사이트를 새로 도는 손을 만들지
않고, 찾은 것을 파일 하나에 더 적는 일만 붙인다.

채용 루틴은 `jobs/latest.json` 을 쓴다. 지면은 `jobs/cfp.json` 을 쓴다.
**두 파일을 섞지 않는다.** 워커가 파일마다 마지막으로 본 자취를 따로 남기므로,
한 파일을 같이 쓰면 뒤에 도는 쪽이 앞의 것을 덮는다.

`jobs/` 는 루틴의 자리다. 세션에서 손대지 않고 `publish.sh` 도 옮기지 않는다.
그래서 이 안내가 `tools/` 에 있다.

---

## 아래를 Self-authorship filter 다음, Output 앞에 붙인다

**Board.** Before creating the Gmail draft, write this run's dated opportunities
to the board. Use the GitHub connector to overwrite `jobs/cfp.json` in the
repository `eeruwang/loggia`. Always use that one path. Never create a new file,
and never touch `jobs/latest.json`, which belongs to the twice-daily jobs
routine. Touch nothing else in the repository. A worker collects the file every
ten minutes.

```json
{"set": {
  "<id>": {
    "id": "<id>",
    "strand": "지면",
    "region": "국제",
    "title": "journal name, special issue title",
    "url": "the call's own page",
    "posted": "YYYY-MM-DD",
    "deadline": "YYYY-MM-DD",
    "note": "one line in Korean",
    "venue": "<venue id or empty string>"
  }
}}
```

`strand` must be exactly `지면`. That value puts the card in the board's
지면과 특집 section. Build `id` from a short venue abbreviation, the year and a
serial. The same `id` overwrites the same card, so reuse it when correcting an
entry later. Write `{"set": {}}` when nothing dated appeared.

Include an opportunity here only when the call states an explicit deadline. The
mail may list rolling calls, but the board cannot, because an undated card does
nothing there. Never guess a date to fill the field.

`venue` is what keeps a deadline in one place. When the call belongs to a
journal in the list below, put its id there. The board then updates that
journal's own deadline instead of standing up a second card, so the same
deadline never lives in two places. Leave it as an empty string for anywhere
else, and the person decides whether to add it as a new venue.

```
actakoreana advancehe aesthetics angelaki arko bja camobs capacious dgs
filmcomment filmphil fss glasgow greyroom humanities iaac ifm ijfma inmun
jaac jac jcms jvc koreajournal kosma leonardo liverpool macdowell mfj miraj
necsus newnham ngc nrfts oaj october opencity orgsound refocus scms screen
senses sophia tcs yonsei
```

---

## 판에서 무슨 일이 일어나나

공고 판의 「지면과 특집」 칸에 선다. 담아두기를 누르면 씨앗이 남고, 다음
갱신에 이렇게 갈린다.

- `venue` 가 적힌 것 → 그 낼 곳의 마감이 바뀐다
- `venue` 가 빈 것 → 낼 곳으로 새로 만들지 사람에게 묻는다

월요일 아침 편지에 「지면 마감」 칸이 붙는다. 예순 날 안으로 들어온 것
가운데 넷까지 보여준다. 다른 요일에는 붙지 않는다.

## 채용 루틴에도 한 줄

`jobs/latest.json` 을 쓰는 채용 루틴의 json 예시 아래에 이 한 줄을 넣는다.

> `strand` 는 `연구소` 아니면 `강의` 둘 중 하나다. 다른 말을 쓰지 않는다.

예시에 `연구소` 만 있고 영국 강의직을 무엇으로 적을지 없어서, 회차마다
영국강의직과 영국강의와 영국과 강의가 섞여 들어왔다. 판은 두 값만 그려서
75건 가운데 60건이 안 보였다. 워커에 갈래를 맞추는 손을 붙여 지금은 무엇이
들어와도 둘로 모이지만, 루틴 쪽에서 못 박아 두는 편이 낫다.

## 채용 루틴의 유령 참조

채용 루틴이 세 군데에서 「Daily opportunities digest」로 일을 떠넘긴다.
그런 루틴은 없다. 도는 것은 셋뿐이다. 매주 영화 리뷰, 매주 논문 받기,
매일 취업 글쓰기 자료 받기.

떠넘겨진 갈래는 레지던시, 전시, 페스티벌, 학회, 저널, Research Fellow와
박사후다. 이 가운데 저널과 학회 CFP 는 매주 논문 받기의 Part B 가 실제로
훑고 있다. 나머지 넷은 지금 아무도 돌지 않는다.
