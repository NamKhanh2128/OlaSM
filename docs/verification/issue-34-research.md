# Issue #34 research — simultaneous booking correction

## Source issue

GitHub issue: [#34 — Hệ thống không phản hồi khi người dùng thay đổi đồng thời điểm đón, điểm đến và loại xe](https://github.com/AI20K-Build-Phase-Cohort-3/P-160/issues/34)

The issue was closed after the simultaneous-change flow was verified on local and staging. Its reported scenario was:

- A booking already has an initial quote, for example with a seven-seat car.
- The user changes pickup, destination, and vehicle type to a four-seat car in one turn.
- The reported result was no response after about 12 seconds, empty fields, and no new quote.
- Reference commit in the issue: `origin/main` (`b7a3b5797d0145b2c5232ce96a2e8e933473417e`).

## Code path reviewed

The current text/core path is implemented through:

- `src/agents/core/agent.py`
- `src/agents/capabilities/booking.py`
- `src/agents/core/booking/state.py`
- `src/agents/core/booking/actions.py`

When `update_booking` receives all three changes, the reducer:

1. Updates the pickup query, destination query, and vehicle type.
2. Clears the resolved locations until the new queries are resolved.
3. Preserves the explicit new vehicle type (`CAR_4`).
4. Invalidates the old fare estimate.
5. Requests pickup search, then destination search, then a new fare estimate.

The current LiveKit-native path also has deterministic quote invalidation and refresh logic in:

- `src/voice_agent/tasks/booking.py`
- `src/voice_agent/session_data.py`

However, its existing regression test directly covers a location change with an existing quote, not the exact three-field change in one voice turn.

## Staging test limitation — mock locations

Staging currently resolves locations from the demo/mock catalog in
`data/gazetteer/place_names.json`. Testers must use one of these exact canonical
names; free-form locations outside this list may leave the location unresolved
and prevent a new quote from being generated.

Supported canonical locations:

1. VinUni
2. Hồ Gươm
3. Hồ Tây
4. Sân bay Nội Bài
5. Lăng Chủ tịch Hồ Chí Minh
6. Văn Miếu - Quốc Tử Giám
7. Quảng trường Ba Đình
8. Nhà hát Lớn Hà Nội
9. Ga Hà Nội
10. Bến xe Mỹ Đình
11. Bến xe Giáp Bát
12. Bến xe Nước Ngầm
13. Đại học Quốc gia Việt Nam
14. Đại học Bách khoa Hà Nội
15. Đại học Kinh tế Quốc dân
16. Đại học Ngoại thương
17. Đại học FPT Hà Nội
18. Học viện Nông nghiệp Việt Nam
19. Keangnam Landmark 72
20. Lotte Center Hà Nội
21. Vincom Center Bà Triệu
22. Vincom Mega Mall Times City
23. Vincom Mega Mall Royal City
24. AEON Mall Long Biên
25. AEON Mall Hà Đông
26. Sân vận động Mỹ Đình
27. Trung tâm Hội nghị Quốc gia
28. Cầu Long Biên
29. Cầu Nhật Tân
30. Cầu Vĩnh Tuy
31. Chợ Đồng Xuân
32. Phố cổ Hà Nội
33. Nhà thờ Lớn Hà Nội
34. Nhà tù Hỏa Lò
35. Hoàng thành Thăng Long
36. Bảo tàng Dân tộc học Việt Nam
37. Bảo tàng Hà Nội
38. Công viên Thủ Lệ
39. Công viên Yên Sở
40. Công viên Cầu Giấy
41. Vườn hoa Lý Thái Tổ
42. Chùa Một Cột
43. Chùa Trấn Quốc
44. Phủ Tây Hồ
45. Phố đi bộ Tràng Tiền
46. Vinhomes Ocean Park
47. Vinhomes Smart City
48. Bệnh viện Bạch Mai
49. Bệnh viện Việt Đức
50. Bệnh viện Trung ương Quân đội 108
51. Bệnh viện K Tân Triều
52. Tháp Rùa

For the two landmarks below, the tester must also choose a valid pickup/drop-off
candidate after the canonical location is resolved:

- `VinUni`: Cổng chính VinUni, Cổng phụ VinUni, or Cổng ký túc xá VinUni.
- `Hồ Gươm`: Đền Ngọc Sơn, Bưu điện Hà Nội, Quảng trường Đông Kinh Nghĩa Thục,
  or Tượng đài Vua Lý Thái Tổ.

Recommended staging reproduction for this issue:

1. Start with pickup `VinUni`, destination `Hồ Gươm`, and a seven-seat car;
   select one valid candidate for each landmark.
2. In one turn, change pickup to `Hồ Tây`, destination to `Vincom Mega Mall Royal
   City`, and the vehicle to a four-seat car.
3. Confirm that both locations and the vehicle update, the old quote is invalidated,
   and a new quote is returned.

The `Bến Thành` value in the reducer probe below is intentionally outside this
Hanoi mock catalog. It validates the reducer sequence only and must not be used
as a staging acceptance location.


## Verification performed

Commands were run with the repository virtualenv through `uv run --no-sync`:

```text
uv run --no-sync pytest -q tests/test_agents/test_model_driven_booking.py tests/test_voice_agent/test_booking_state.py
35 passed in 0.42s

uv run --no-sync pytest -q tests/test_agents tests/test_voice_agent/test_booking_state.py
254 passed in 0.81s

uv run --no-sync pytest -q tests/test_voice_agent/test_booking_task.py tests/test_voice_agent/test_persistence.py tests/test_voice_agent/test_server.py
40 passed in 1.76s
```

An additional no-file probe reproduced the issue sequence on the current core path:

```text
existing quote: pickup=VinUni, destination=Royal City, vehicle=CAR_7
user change: pickup=Bến Thành, destination=Hồ Gươm, vehicle=CAR_4
actions: search_place(pickup) → search_place(destination) → estimate_fare
final state: Bến Thành, Hồ Gươm, CAR_4, fare-new=90,000 VND
```

## Conclusion

The current core booking implementation passes the issue-shaped deterministic probe and the related test suites. There is no evidence of the reported “empty fields/no re-quote” failure in this local path.

Local and staging user testing confirmed that changing the pickup, destination, and vehicle together works when valid mock locations are used. The staging limitation above explains failures with unsupported location names. A dedicated end-to-end regression test for a single user utterance changing both locations and vehicle after an existing quote would provide stronger automated coverage.

