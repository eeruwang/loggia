# 지면 루틴

주 한 번, 월요일 아침에 돈다. 길목을 훑어 특집과 호별 모집 마감을 찾아
저장소의 `jobs/cfp.json` 에 쓴다. 워커가 열 분마다 걷어 판으로 옮긴다.

채용 루틴은 `jobs/latest.json` 에 쓴다. **두 파일을 섞지 않는다.**
한 파일을 같이 쓰면 뒤에 도는 쪽이 앞의 것을 덮는다.

`jobs/` 는 루틴의 자리다. 세션에서 손대지 않는다. `publish.sh` 도 그 폴더를
옮기지 않는다. 그래서 이 안내가 여기 있다.

## 왜 주 한 번인가

특집 마감은 두세 달 앞에 뜨고 사이트가 매일 바뀌지 않는다. 채용과 같은
주기로 돌리면 같은 것을 여든 번 다시 읽는다.

## 길목

데이터의 `watch` 에 적혀 있다. 지금 여덟이다.

| 어디 | 무엇 |
| --- | --- |
| H-Net Film Studies | 영화 저널 특집 |
| PhilEvents | 철학 저널 특집 |
| ArtHist.net | 미술사와 매체예술 |
| e-flux | 동시대 미술 지면 |
| MDPI Humanities 특집 | 특집 마감 |
| Intellect CFP | MIRAJ 등 |
| 한국영상학회 공지 | 호별 모집과 마감 연장 |
| 클래리베이트 MJL | 색인 등급 확인. 새 마감이 뜨는 자리는 아니다 |

## 무엇을 고르나

분위기, 일기적 무빙이미지, 영화철학, 미학, 매체예술. 이 다섯에 걸리는 것만
줍는다. 마감이 이미 지난 것과 마감을 못 찾은 것은 줍지 않는다. 지면 마감은
날짜가 없으면 판에서 아무 일도 하지 못한다.

## 어떤 꼴로 쓰나

```json
{"set": {
  "<id>": {
    "id": "<id>",
    "strand": "지면",
    "region": "국제|한국",
    "title": "지면 이름, 특집 제목",
    "url": "공고 주소",
    "posted": "YYYY-MM-DD",
    "deadline": "YYYY-MM-DD",
    "note": "분량, 주제, 확인한 것과 확인 못한 것",
    "venue": "<낼 곳 id 또는 비움>"
  }
}}
```

`strand` 는 반드시 `지면` 이다. 이 값으로 판에서 「지면과 특집」 칸에 선다.

`venue` 가 이 루틴의 핵심이다. **이미 판에 있는 곳이면 그 id를 적는다.**
그러면 담아두기를 눌렀을 때 카드가 항목으로 심기지 않고 그 낼 곳의 마감만
갈아 끼워진다. 마감이 두 자리에 생기지 않는다. 판에 없는 곳이면 비워 둔다.

지금 판에 있는 낼 곳의 id는 이렇다.

```
actakoreana advancehe aesthetics angelaki arko bja camobs capacious dgs
filmcomment filmphil fss glasgow greyroom humanities iaac ifm ijfma inmun
jaac jac jcms jvc koreajournal kosma leonardo liverpool macdowell mfj miraj
necsus newnham ngc nrfts oaj october opencity orgsound refocus scms screen
senses sophia tcs yonsei
```

## 지어내지 않는다

마감을 못 찾으면 그 자리를 비우지 말고 그 항목을 통째로 뺀다. 원문을 열지
못했으면 `note` 에 그렇게 적는다. 짐작한 날짜를 확정처럼 적지 않는다.

## 판에서 무슨 일이 일어나나

공고 판의 「지면과 특집」 칸에 선다. 담아두기를 누르면 씨앗이 남는다.

- `venue` 가 적힌 것 → 다음 갱신에 그 낼 곳의 마감이 바뀐다
- `venue` 가 빈 것 → 낼 곳으로 새로 만들지 사람에게 묻는다

월요일 아침 편지에 「지면 마감」 칸이 붙는다. 예순 날 안으로 들어온 것
가운데 넷까지 보여준다. 다른 요일에는 붙지 않는다.
