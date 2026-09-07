/**
 * 评审数据本地存储与聚合
 * localStorage key: review-analytics-v1
 */
(function (global) {
  const STORAGE_KEY = 'review-analytics-v1';
  const MIN_READ_SECONDS = 45; // 默认按 7000 字档；实际按字数动态计算

  function getMinReadSecondsByChars(chars) {
    if (chars <= 5500) return 30;
    if (chars <= 8500) return 45;
    return 70;
  }
  const DEMO_USER_ID = 'demo-user-001';

  const Q1_LABELS = {
    star5: '5星',
    star4: '4星',
    star3: '3星',
    star2: '2星',
    star1: '1星',
    // 兼容旧数据
    great: '很好看',
    good: '比较好看',
    average: '一般',
    bad: '不太好看',
    terrible: '很难看',
  };

  const Q1_SCORES = {
    star5: 5,
    star4: 4,
    star3: 3,
    star2: 2,
    star1: 1,
    great: 5,
    good: 4,
    average: 3,
    bad: 2,
    terrible: 1,
  };

  function todayKey() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  function loadStore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return { reviews: [], skips: [] };
  }

  function saveStore(store) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  }

  function saveReview(payload) {
    const store = loadStore();
    const record = {
      id: `r_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      userId: payload.userId || DEMO_USER_ID,
      bookId: payload.bookId,
      bookName: payload.bookName,
      chapterIndex: payload.chapterIndex,
      displayChars: payload.displayChars || 0,
      readSeconds: payload.readSeconds || 0,
      minReadSeconds: payload.minReadSeconds || MIN_READ_SECONDS,
      tooFast: !!payload.tooFast,
      answers: payload.answers || {},
      q1Score: payload.answers?.scores?.q1
        ?? Q1_SCORES[payload.answers?.q1]
        ?? null,
      q4Score: payload.answers?.scores?.q4 ?? null,
      q5Score: payload.answers?.scores?.q5 ?? null,
      collected: payload.answers?.collect === true,
      collectSkipped: payload.answers?.collect == null,
      createdAt: new Date().toISOString(),
      dateKey: todayKey(),
    };
    store.reviews.push(record);
    saveStore(store);
    return record;
  }

  function saveSkip(payload) {
    const store = loadStore();
    store.skips.push({
      id: `s_${Date.now()}`,
      userId: payload.userId || DEMO_USER_ID,
      bookId: payload.bookId,
      bookName: payload.bookName,
      reason: payload.reason,
      createdAt: new Date().toISOString(),
      dateKey: todayKey(),
    });
    saveStore(store);
  }

  function pct(part, total) {
    if (!total) return '0%';
    return `${((part / total) * 100).toFixed(1)}%`;
  }

  function avg(nums) {
    if (!nums.length) return 0;
    return nums.reduce((a, b) => a + b, 0) / nums.length;
  }

  function buildBookStats(reviews) {
    const byBook = {};
    reviews.forEach((r) => {
      const key = String(r.bookId || r.bookName);
      if (!byBook[key]) {
        byBook[key] = {
          bookId: r.bookId,
          bookName: r.bookName,
          reviews: [],
        };
      }
      byBook[key].reviews.push(r);
    });

    return Object.values(byBook).map((book) => {
      const list = book.reviews;
      const q1Counts = {};
      Object.keys(Q1_LABELS).forEach((k) => { q1Counts[k] = 0; });
      list.forEach((r) => {
        if (r.answers?.q1) q1Counts[r.answers.q1] = (q1Counts[r.answers.q1] || 0) + 1;
      });

      const scores = list.map((r) => r.q1Score).filter((n) => n != null);
      const durations = list.map((r) => r.readSeconds);
      const collectYes = list.filter((r) => r.collected).length;
      const collectAnswered = list.filter((r) => r.answers?.collect === true || r.answers?.collect === false).length;

      return {
        bookId: book.bookId,
        bookName: book.bookName,
        reviewCount: list.length,
        q1Counts,
        q1Percents: Object.fromEntries(
          Object.keys(Q1_LABELS).map((k) => [k, pct(q1Counts[k], list.length)])
        ),
        avgScore: Number(avg(scores).toFixed(2)),
        durations,
        avgDuration: Math.round(avg(durations)),
        tooFastCount: list.filter((r) => r.tooFast).length,
        collectRate: collectAnswered ? pct(collectYes, collectAnswered) : '0%',
        collectYes,
        collectAnswered,
        reviews: list,
      };
    }).sort((a, b) => b.reviewCount - a.reviewCount);
  }

  function buildUserStats(reviews) {
    const byUser = {};
    reviews.forEach((r) => {
      if (!byUser[r.userId]) byUser[r.userId] = [];
      byUser[r.userId].push(r);
    });

    return Object.entries(byUser).map(([userId, list]) => {
      const today = todayKey();
      const todayList = list.filter((r) => r.dateKey === today);
      const scores = list.map((r) => r.q1Score).filter((n) => n != null);
      const durations = list.map((r) => r.readSeconds);
      const bookScores = list.map((r) => ({
        bookId: r.bookId,
        bookName: r.bookName,
        score: r.q1Score,
        readSeconds: r.readSeconds,
        tooFast: r.tooFast,
        collected: r.collected,
        createdAt: r.createdAt,
      }));

      return {
        userId,
        totalReviews: list.length,
        dailyReviews: todayList.length,
        durations,
        avgDuration: Math.round(avg(durations)),
        bookScores,
        avgBookScore: Number(avg(scores).toFixed(2)),
        tooFastCount: list.filter((r) => r.tooFast).length,
        collectCount: list.filter((r) => r.collected).length,
        collectRate: pct(list.filter((r) => r.collected).length, list.filter((r) => r.answers?.collect === true || r.answers?.collect === false).length || list.length),
      };
    }).sort((a, b) => b.totalReviews - a.totalReviews);
  }

  function getAnalytics() {
    const store = loadStore();
    const reviews = store.reviews || [];
    const books = buildBookStats(reviews);
    const users = buildUserStats(reviews);
    const collectYes = reviews.filter((r) => r.collected).length;
    const collectAnswered = reviews.filter((r) => r.answers?.collect === true || r.answers?.collect === false).length;

    return {
      summary: {
        totalReviews: reviews.length,
        totalBooks: books.length,
        totalUsers: users.length,
        avgScore: Number(avg(reviews.map((r) => r.q1Score).filter((n) => n != null)).toFixed(2)),
        avgDuration: Math.round(avg(reviews.map((r) => r.readSeconds))),
        tooFastRate: pct(reviews.filter((r) => r.tooFast).length, reviews.length),
        collectRate: collectAnswered ? pct(collectYes, collectAnswered) : '0%',
        skipCount: (store.skips || []).length,
      },
      books,
      users,
      reviews,
      skips: store.skips || [],
      q1Labels: Q1_LABELS,
      minReadSeconds: MIN_READ_SECONDS,
    };
  }

  function clearAll() {
    localStorage.removeItem(STORAGE_KEY);
  }

  function seedDemoIfEmpty() {
    const store = loadStore();
    if (store.reviews.length) return false;
    // no auto seed by default
    return false;
  }

  global.ReviewAnalytics = {
    MIN_READ_SECONDS,
    DEMO_USER_ID,
    Q1_LABELS,
    Q1_SCORES,
    getMinReadSecondsByChars,
    saveReview,
    saveSkip,
    getAnalytics,
    clearAll,
    loadStore,
    seedDemoIfEmpty,
  };
})(window);
