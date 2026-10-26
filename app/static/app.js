'use strict';

/* ============ утилиты ============ */
const $app = document.getElementById('app');
const SUPPORTED_LOCALES = ['ru', 'kk', 'en'];
const cachedUser = JSON.parse(sessionStorage.getItem('aqyl_user') || 'null');
const initialLocale = localStorage.getItem('aqyl_locale') || cachedUser?.locale ||
  (navigator.languages || [navigator.language]).map((x) => x.toLowerCase().split('-')[0])
    .find((x) => SUPPORTED_LOCALES.includes(x)) || 'ru';
const TRANSLATIONS = {
  kk: {
    'Приёмы': 'Қабылдаулар', 'Новый приём': 'Жаңа қабылдау', 'Администрирование': 'Әкімшілік',
    'Выйти': 'Шығу', 'Войти': 'Кіру', 'Email': 'Электрондық пошта', 'Пароль': 'Құпиясөз',
    'Помощник врача: превращает запись приёма в черновик заключения.': 'Дәрігер көмекшісі: қабылдау жазбасын қорытынды жобасына айналдырады.',
    'Аудиозапись': 'Аудиожазба', 'Готовый текст': 'Дайын мәтін', 'Пациент': 'Пациент',
    'Дата приёма': 'Қабылдау күні', 'Запись с микрофона': 'Микрофоннан жазу',
    'Начать запись': 'Жазуды бастау', 'Остановить': 'Тоқтату', 'Пауза': 'Үзіліс',
    'Продолжить': 'Жалғастыру', 'Записать заново': 'Қайта жазу', 'Запись готова': 'Жазба дайын',
    'Согласие': 'Келісім', 'Текст разговора': 'Әңгіме мәтіні',
    'Создать черновик заключения': 'Қорытынды жобасын жасау', 'Жалобы': 'Шағымдар',
    'Анамнез': 'Анамнез', 'Симптомы и сроки': 'Белгілер мен ұзақтығы',
    'Объективные данные': 'Объективті деректер', 'Диагноз': 'Диагноз',
    'План лечения': 'Емдеу жоспары', 'Рекомендации': 'Ұсыныстар',
    'Требует уточнения': 'Нақтылауды қажет етеді', 'Памятка пациенту': 'Пациентке арналған жадынама',
    'Медицинское заключение': 'Медициналық қорытынды', 'Подтвердить заключение': 'Қорытындыны растау',
    'Сохранить правки': 'Өзгерістерді сақтау', 'Скачать Word': 'Word файлын жүктеу',
    'Печать': 'Басып шығару', 'Диалог': 'Диалог', 'Запись': 'Жазба',
    'Проверка': 'Тексеру', 'К списку': 'Тізімге оралу', 'Расходы': 'Шығындар',
    'Пользователи': 'Пайдаланушылар', 'Журнал': 'Журнал', 'Система': 'Жүйе',
    'МКБ-10': 'АХЖ-10', 'Код МКБ-10': 'АХЖ-10 коды',
    'Русский': 'Русский', 'Қазақша': 'Қазақша', 'English': 'English',
    'Код из письма': 'Хаттағы код', 'Подтвердить код': 'Кодты растау',
    'Код подтверждения отправлен на email': 'Растау коды электрондық поштаға жіберілді',
    'Забыли пароль?': 'Құпиясөзді ұмыттыңыз ба?', 'Новый пароль': 'Жаңа құпиясөз',
    'Восстановление пароля': 'Құпиясөзді қалпына келтіру', 'Сохранить пароль': 'Құпиясөзді сақтау',
    'Отправить ссылку': 'Сілтемені жіберу', 'Вернуться ко входу': 'Кіру бетіне оралу',
    'Подтверждение email': 'Электрондық поштаны растау', 'Проверяем ссылку…': 'Сілтеме тексерілуде…',
    'Перейти ко входу': 'Кіру бетіне өту',
    'Поиск по пациенту или врачу': 'Пациент немесе дәрігер бойынша іздеу',
    'Статус': 'Күй', 'Все статусы': 'Барлық күйлер', 'Обработка': 'Өңделуде',
    'Черновик': 'Жоба', 'Подтверждено': 'Расталды', 'Ошибка': 'Қате',
    'Ничего не найдено.': 'Ештеңе табылмады.',
    'Приёмов пока нет. Загрузите запись или вставьте текст разговора.': 'Қабылдаулар әлі жоқ. Жазбаны жүктеңіз немесе мәтінді енгізіңіз.',
    'Дата приёма': 'Қабылдау күні', 'Врач': 'Дәрігер', 'Источник': 'Дереккөз',
    'Аудио': 'Аудио', 'Текст': 'Мәтін', 'Или загрузите файл': 'Немесе файлды жүктеңіз',
    'WAV, MP3, M4A, OGG, FLAC, WebM. Обработка занимает 1–3 минуты.': 'WAV, MP3, M4A, OGG, FLAC, WebM. Өңдеу 1–3 минут алады.',
    'Пациент дал согласие на запись и обработку разговора': 'Пациент сөйлесуді жазуға және өңдеуге келісім берді',
    'Каждую реплику с новой строки, с пометкой «Врач:» или «Пациент:».': 'Әр репликаны жаңа жолдан «Дәрігер:» немесе «Пациент:» белгісімен жазыңыз.',
    'Браузер не поддерживает запись. Загрузите готовый файл.': 'Браузер жазуды қолдамайды. Дайын файлды жүктеңіз.',
    'Нет доступа к микрофону. Разрешите его в браузере (нужен HTTPS или localhost).': 'Микрофонға рұқсат жоқ. Браузерде рұқсат беріңіз (HTTPS немесе localhost қажет).',
    'Запишите разговор или выберите файл.': 'Сөйлесуді жазыңыз немесе файлды таңдаңыз.',
    'Подтвердите согласие пациента на запись.': 'Пациенттің жазуға келісімін растаңыз.',
    'Результат — черновик. Он не попадает в карту, пока вы его не проверите и не подтвердите.': 'Нәтиже — жоба. Тексеріп, растамайынша картаға енгізілмейді.',
    'Загрузка…': 'Жүктелуде…', 'Готовим черновик': 'Жоба дайындалуда',
    'Страницу можно закрыть — обработка продолжится на сервере.': 'Бетті жабуға болады — өңдеу серверде жалғасады.',
    'В очереди': 'Кезекте', 'Определяем, кто говорит': 'Сөйлеушілер анықталуда',
    'Распознаём речь': 'Сөйлеу танылуда', 'Разбираем диалог и роли': 'Диалог пен рөлдер талдануда',
    'Готовим заключение и памятку': 'Қорытынды мен жадынама дайындалуда',
    'Симптомы и сроки': 'Белгілер мен ұзақтығы', 'По одному пункту в строке.': 'Әр жолға бір тармақтан.',
    'Проверить значения по записи': 'Мәндерді жазбамен салыстырыңыз',
    'Все числа и дозировки из заключения найдены в диалоге.': 'Қорытындыдағы барлық сандар мен дозалар диалогтан табылды.',
    'Нет диалога для сверки.': 'Салыстыруға арналған диалог жоқ.',
    'ИИ не нашёл в разговоре': 'ЖИ әңгімеден таппады', 'Заметки по расшифровке': 'Транскрипция ескертпелері',
    'Проверка автоматическая и не заменяет вашу: она ищет только числа с единицами измерения.': 'Автоматты тексеру дәрігер тексеруін алмастырмайды; тек өлшем бірліктері бар сандарды іздейді.',
    'Сохранено': 'Сақталды', 'Сохранить правки': 'Өзгерістерді сақтау',
    'Сохранить диалог': 'Диалогты сақтау', 'Править текст': 'Мәтінді өңдеу',
    'Закрыть редактор': 'Өңдегішті жабу', 'Поменять роли': 'Рөлдерді ауыстыру',
    'Обновить заключение по диалогу': 'Диалог бойынша қорытындыны жаңарту',
    'Запись удалена': 'Жазба жойылды', 'Удалить запись': 'Жазбаны жою',
    'Подтвердить заключение?': 'Қорытындыны растайсыз ба?',
    'Подтверждаю': 'Растаймын', 'Вы подтверждаете, что проверили текст и несёте ответственность за его содержание.': 'Мәтінді тексергеніңізді және оның мазмұнына жауапты екеніңізді растайсыз.',
    'Заменить правки?': 'Өзгерістерді ауыстыру керек пе?', 'Заменить': 'Ауыстыру',
    'Расходы за месяц': 'Айлық шығындар', 'Обработано приёмов': 'Өңделген қабылдаулар',
    'Средняя стоимость приёма': 'Бір қабылдаудың орташа құны',
    'Новый пользователь': 'Жаңа пайдаланушы', 'ФИО': 'Толық аты-жөні',
    'Специальность': 'Мамандық', 'Не выбрана': 'Таңдалмаған',
    'Создать': 'Құру', 'Отключить': 'Өшіру', 'Включить': 'Қосу',
    'Справочник специальностей': 'Мамандықтар анықтамалығы',
    'Название на русском': 'Орысша атауы', 'Қазақша атауы': 'Қазақша атауы',
    'Добавить специальность': 'Мамандық қосу', 'Шаблон медицинского документа': 'Медициналық құжат үлгісі',
    'Сначала добавьте специальность.': 'Алдымен мамандықты қосыңыз.',
    'Сохранить шаблон': 'Үлгіні сақтау', 'Импорт справочника МКБ-10': 'АХЖ-10 анықтамалығын импорттау',
    'Импортировать': 'Импорттау',
    'Загрузите проверенный JSON-массив. Каждая запись содержит code, name_ru и при наличии name_kk/name_en.': 'Тексерілген JSON массивін жүктеңіз. Әр жазбада code, name_ru және қажет болса name_kk/name_en болуы керек.',
    'Система': 'Жүйе', 'Время': 'Уақыт', 'Пользователь': 'Пайдаланушы',
    'Действие': 'Әрекет',     'Объект': 'Нысан', 'Детали': 'Мәліметтер', 'Запись приостановлена': 'Жазба уақытша тоқтатылды',
    'Идёт запись': 'Жазу жүріп жатыр',
    'Подтвердить': 'Растау', 'Код подтверждения отправлен на email': 'Растау коды электрондық поштаға жіберілді',
    'Месяц (ГГГГ-ММ)': 'Ай (ЖЖЖЖ-АА)', 'Месяц ГГГГ-ММ': 'Ай ЖЖЖЖ-АА',
  },
  en: {
    'Приёмы': 'Consultations', 'Новый приём': 'New consultation', 'Администрирование': 'Administration',
    'Выйти': 'Log out', 'Войти': 'Sign in', 'Email': 'Email', 'Пароль': 'Password',
    'Помощник врача: превращает запись приёма в черновик заключения.': 'Clinical assistant that turns a visit recording into a draft medical note.',
    'Аудиозапись': 'Audio recording', 'Готовый текст': 'Existing transcript', 'Пациент': 'Patient',
    'Дата приёма': 'Visit date', 'Запись с микрофона': 'Microphone recording',
    'Начать запись': 'Start recording', 'Остановить': 'Stop', 'Пауза': 'Pause',
    'Продолжить': 'Resume', 'Записать заново': 'Record again', 'Запись готова': 'Recording ready',
    'Согласие': 'Consent', 'Текст разговора': 'Consultation transcript',
    'Создать черновик заключения': 'Create draft note', 'Жалобы': 'Chief complaints',
    'Анамнез': 'History', 'Симптомы и сроки': 'Symptoms and duration',
    'Объективные данные': 'Examination', 'Диагноз': 'Diagnosis',
    'План лечения': 'Treatment plan', 'Рекомендации': 'Recommendations',
    'Требует уточнения': 'Needs clarification', 'Памятка пациенту': 'Patient instructions',
    'Медицинское заключение': 'Medical note', 'Подтвердить заключение': 'Confirm note',
    'Сохранить правки': 'Save changes', 'Скачать Word': 'Download Word',
    'Печать': 'Print', 'Диалог': 'Transcript', 'Запись': 'Recording',
    'Проверка': 'Review', 'К списку': 'Back to list', 'Расходы': 'Usage',
    'Пользователи': 'Users', 'Журнал': 'Audit log', 'Система': 'System',
    'МКБ-10': 'ICD-10', 'Код МКБ-10': 'ICD-10 code',
    'Русский': 'Русский', 'Қазақша': 'Қазақша', 'English': 'English',
    'Код из письма': 'Email code', 'Подтвердить код': 'Verify code',
    'Код подтверждения отправлен на email': 'A verification code was emailed to you',
    'Забыли пароль?': 'Forgot password?', 'Новый пароль': 'New password',
    'Восстановление пароля': 'Password recovery', 'Сохранить пароль': 'Save password',
    'Отправить ссылку': 'Send reset link', 'Вернуться ко входу': 'Back to sign in',
    'Подтверждение email': 'Email verification', 'Проверяем ссылку…': 'Checking link…',
    'Перейти ко входу': 'Go to sign in',
    'Поиск по пациенту или врачу': 'Search by patient or doctor',
    'Статус': 'Status', 'Все статусы': 'All statuses', 'Обработка': 'Processing',
    'Черновик': 'Draft', 'Подтверждено': 'Confirmed', 'Ошибка': 'Failed',
    'Ничего не найдено.': 'No results found.',
    'Приёмов пока нет. Загрузите запись или вставьте текст разговора.': 'No consultations yet. Upload a recording or paste a transcript.',
    'Дата приёма': 'Visit date', 'Врач': 'Doctor', 'Источник': 'Source',
    'Аудио': 'Audio', 'Текст': 'Text', 'Или загрузите файл': 'Or upload a file',
    'WAV, MP3, M4A, OGG, FLAC, WebM. Обработка занимает 1–3 минуты.': 'WAV, MP3, M4A, OGG, FLAC, WebM. Processing takes 1–3 minutes.',
    'Пациент дал согласие на запись и обработку разговора': 'The patient consented to recording and processing',
    'Каждую реплику с новой строки, с пометкой «Врач:» или «Пациент:».': 'Put each turn on a new line, labeled “Doctor:” or “Patient:”.',
    'Браузер не поддерживает запись. Загрузите готовый файл.': 'This browser does not support recording. Upload an audio file.',
    'Нет доступа к микрофону. Разрешите его в браузере (нужен HTTPS или localhost).': 'Microphone access denied. Allow access in the browser (HTTPS or localhost required).',
    'Запишите разговор или выберите файл.': 'Record a consultation or choose a file.',
    'Подтвердите согласие пациента на запись.': 'Confirm the patient’s consent to recording.',
    'Результат — черновик. Он не попадает в карту, пока вы его не проверите и не подтвердите.': 'The result is a draft and is not added to the record until reviewed and confirmed.',
    'Загрузка…': 'Loading…', 'Готовим черновик': 'Preparing draft',
    'Страницу можно закрыть — обработка продолжится на сервере.': 'You can close this page; processing continues on the server.',
    'В очереди': 'Queued', 'Определяем, кто говорит': 'Identifying speakers',
    'Распознаём речь': 'Transcribing speech', 'Разбираем диалог и роли': 'Analyzing dialogue and roles',
    'Готовим заключение и памятку': 'Preparing note and patient instructions',
    'Симптомы и сроки': 'Symptoms and duration', 'По одному пункту в строке.': 'One item per line.',
    'Проверить значения по записи': 'Verify values against recording',
    'Все числа и дозировки из заключения найдены в диалоге.': 'All numbers and doses in the note were found in the dialogue.',
    'Нет диалога для сверки.': 'No dialogue is available for review.',
    'ИИ не нашёл в разговоре': 'Not found in the conversation', 'Заметки по расшифровке': 'Transcription notes',
    'Проверка автоматическая и не заменяет вашу: она ищет только числа с единицами измерения.': 'Automated review is not a substitute for clinician review; it only checks numbers with units.',
    'Сохранено': 'Saved', 'Сохранить правки': 'Save changes',
    'Сохранить диалог': 'Save transcript', 'Править текст': 'Edit text',
    'Закрыть редактор': 'Close editor', 'Поменять роли': 'Swap roles',
    'Обновить заключение по диалогу': 'Regenerate note from transcript',
    'Запись удалена': 'Recording deleted', 'Удалить запись': 'Delete recording',
    'Подтвердить заключение?': 'Confirm this note?',
    'Подтверждаю': 'Confirm', 'Вы подтверждаете, что проверили текст и несёте ответственность за его содержание.': 'You confirm that you reviewed the text and accept responsibility for its contents.',
    'Заменить правки?': 'Replace edits?', 'Заменить': 'Replace',
    'Расходы за месяц': 'Monthly usage', 'Обработано приёмов': 'Consultations processed',
    'Средняя стоимость приёма': 'Average cost per consultation',
    'Новый пользователь': 'New user', 'ФИО': 'Full name',
    'Специальность': 'Specialty', 'Не выбрана': 'Not selected',
    'Создать': 'Create', 'Отключить': 'Deactivate', 'Включить': 'Activate',
    'Справочник специальностей': 'Specialty directory',
    'Название на русском': 'Name in Russian', 'Қазақша атауы': 'Name in Kazakh',
    'Добавить специальность': 'Add specialty', 'Шаблон медицинского документа': 'Medical document template',
    'Сначала добавьте специальность.': 'Add a specialty first.',
    'Сохранить шаблон': 'Save template', 'Импорт справочника МКБ-10': 'Import ICD-10 catalog',
    'Импортировать': 'Import',
    'Загрузите проверенный JSON-массив. Каждая запись содержит code, name_ru и при наличии name_kk/name_en.': 'Upload a verified JSON array. Each item needs code, name_ru and optionally name_kk/name_en.',
    'Время': 'Time', 'Пользователь': 'User', 'Действие': 'Action',
    'Объект': 'Object', 'Детали': 'Details', 'Запись приостановлена': 'Recording paused',
    'Идёт запись': 'Recording',
    'Подтвердить': 'Verify',
    'Месяц (ГГГГ-ММ)': 'Month (YYYY-MM)', 'Месяц ГГГГ-ММ': 'Month YYYY-MM',
  },
};
Object.assign(TRANSLATIONS.kk, {
  'Поля: complaints, anamnesis, symptoms_duration, examination, diagnosis, diagnosis_code, treatment_plan, recommendations.': 'Өрістер: complaints, anamnesis, symptoms_duration, examination, diagnosis, diagnosis_code, treatment_plan, recommendations.',
  "Тип документа": "Құжат түрі",
  "Первичный приём": "Алғашқы қабылдау",
  "Осмотр": "Тексеру",
  "Выписка": "Үзінді көшірме",
  "Справочники": "Анықтамалықтар",
  "Загрузить JSON": "JSON жүктеу",
  "Скачать пример JSON": "JSON үлгісін жүктеу",
  "Загрузить специальности": "Мамандықтарды жүктеу",
  "Файл больше 10 МБ": "Файл 10 МБ-тан үлкен",
  "Некорректный JSON": "JSON пішімі қате",
  "Название специальности": "Мамандық атауы",
  "Администратор": "Әкімші",
  "Email подтверждён": "Email расталды",
  "Email подтверждён. Теперь войдите в AqylMed.": "Email расталды. AqylMed жүйесіне кіріңіз.",
  "В ссылке отсутствует токен подтверждения.": "Сілтемеде растау коды жоқ.",
  "Введите код или название, выберите код из справочника.": "Кодты немесе атауын енгізіп, анықтамалықтан таңдаңыз.",
  "Поиск по коду или названию МКБ-10": "АХЖ-10 коды немесе атауы бойынша іздеу",
  "Вернуть": "Қайтару",
  "Вернуть к редактированию": "Өңдеуге қайтару",
  "Вернуть к редактированию?": "Өңдеуге қайтару керек пе?",
  "Да": "Иә",
  "Нет": "Жоқ",
  "Диалог недоступен.": "Диалог қолжетімсіз.",
  "Диалог сохранён. Нажмите «Обновить заключение».": "Диалог сақталды. Қорытындыны жаңартыңыз.",
  "Если ИИ перепутал, кто врач, а кто пациент, поменяйте роли и обновите заключение.": "ЖИ дәрігер мен пациентті шатастырса, рөлдерді ауыстырып, қорытындыны жаңартыңыз.",
  "Есть несохранённые правки": "Сақталмаған өзгерістер бар",
  "За этот месяц расходов нет": "Осы айда шығын жоқ",
  "Загрузить запись для прослушивания": "Тыңдау үшін жазбаны жүктеу",
  "Заключение ещё не создано.": "Қорытынды әлі жасалмаған.",
  "Заключение подтверждено": "Қорытынды расталды",
  "Источник разговора": "Әңгіме дереккөзі",
  "К списку приёмов": "Қабылдаулар тізіміне",
  "Минут аудио": "Аудио минуттары",
  "Модель": "Модель",
  "Нет связи с сервером. Проверьте подключение.": "Сервермен байланыс жоқ. Қосылымды тексеріңіз.",
  "Новый черновик заменит текст заключения и памятки, который вы уже исправили.": "Жаңа жоба түзетілген қорытынды мен жадынаманы ауыстырады.",
  "Ожидается JSON-массив кодов": "Кодтардың JSON массиві қажет",
  "Отмена": "Бас тарту",
  "Пароль изменён. Теперь войдите.": "Құпиясөз өзгертілді. Жүйеге кіріңіз.",
  "Повторить обработку": "Қайта өңдеу",
  "Подготовлено с помощью AqylMed AI. Документ должен быть проверен врачом.": "AqylMed AI көмегімен әзірленген. Құжатты дәрігер тексеруі керек.",
  "Подтверждение будет снято, действие попадёт в журнал.": "Растау алынып тасталады, әрекет журналға жазылады.",
  "Пользователь создан": "Пайдаланушы құрылды",
  "Последний вход": "Соңғы кіру",
  "Правки сохранены": "Өзгерістер сақталды",
  "Приём создан из текста, аудио нет.": "Қабылдау мәтіннен жасалған, аудио жоқ.",
  "Провайдер": "Провайдер",
  "Проверьте JSON шаблона": "Үлгінің JSON пішімін тексеріңіз",
  "Проверьте JSON-массив кодов МКБ-10": "АХЖ-10 кодтарының JSON массивін тексеріңіз",
  "Проверьте значения по записи": "Мәндерді жазбамен салыстырыңыз",
  "Распознавание речи": "Сөйлеуді тану",
  "Речь": "Сөйлеу",
  "Роли «Врач» и «Пациент» поменялись местами": "Дәрігер мен пациент рөлдері ауыстырылды",
  "Роль": "Рөл",
  "Сессия истекла. Войдите снова.": "Сессия аяқталды. Қайта кіріңіз.",
  "Специальность добавлена": "Мамандық қосылды",
  "Ссылка подтверждения отправлена": "Растау сілтемесі жіберілді",
  "Стоимость": "Құны",
  "Тип": "Түрі",
  "Токены вход / выход": "Кіріс / шығыс токендері",
  "Удалить": "Жою",
  "Удалить аудиозапись?": "Аудиожазбаны жою керек пе?",
  "Файл будет удалён без возможности восстановления. Текст и заключение сохранятся.": "Файл біржола жойылады. Мәтін мен қорытынды сақталады.",
  "Фамилия И. О.": "Тегі А. Ә.",
  "Черновик, не подтверждён": "Расталмаған жоба",
  "Шаблон сохранён": "Үлгі сақталды",
  "Язык интерфейса": "Интерфейс тілі",
  "не указано": "көрсетілмеген",
  "нет": "жоқ",
  "Двухфакторная аутентификация": "Екі факторлы аутентификация",
  "SMTP настроен": "SMTP бапталған",
  "Email-уведомления об изменении пароля": "Құпиясөз өзгергені туралы email",
  "ffmpeg установлен": "ffmpeg орнатылған",
  "Диаризация (кто говорит)": "Сөйлеушілерді ажырату",
  "Месячный лимит расходов": "Айлық шығын шегі",
  "Удалять аудио после обработки": "Өңдеуден кейін аудионы жою",
  "Хранение аудио": "Аудионы сақтау",
  "Языковая модель": "Тілдік модель",
  "без ограничения": "шектеусіз",
  "выключена, роли определяет языковая модель": "өшірілген, рөлдерді тілдік модель анықтайды",
  "не задан": "берілмеген",
  "Подтверждено:": "Расталды:",
  "Врач:": "Дәрігер:",
  "приём": "қабылдау",
  "Импортировано кодов:": "Импортталған кодтар:",
  "Удалено записей:": "Жойылған жазбалар:",
  "Лимит не задан": "Шектеу қойылмаған",
  "Врач: Здравствуйте, что вас беспокоит?\nПациент: …": "Дәрігер: Сәлеметсіз бе, не мазалайды?\nПациент: …"
});
Object.assign(TRANSLATIONS.en, {
  'Поля: complaints, anamnesis, symptoms_duration, examination, diagnosis, diagnosis_code, treatment_plan, recommendations.': 'Fields: complaints, anamnesis, symptoms_duration, examination, diagnosis, diagnosis_code, treatment_plan, recommendations.',
  "Тип документа": "Document type",
  "Первичный приём": "Initial consultation",
  "Осмотр": "Examination",
  "Выписка": "Discharge summary",
  "Справочники": "Catalogs",
  "Загрузить JSON": "Upload JSON",
  "Скачать пример JSON": "Download JSON example",
  "Загрузить специальности": "Upload specialties",
  "Файл больше 10 МБ": "File exceeds 10 MB",
  "Некорректный JSON": "Invalid JSON",
  "Название специальности": "Specialty name",
  "Администратор": "Administrator",
  "Email подтверждён": "Email verified",
  "Email подтверждён. Теперь войдите в AqylMed.": "Email verified. You can now sign in to AqylMed.",
  "В ссылке отсутствует токен подтверждения.": "The link has no verification token.",
  "Введите код или название, выберите код из справочника.": "Enter a code or name and select a catalog entry.",
  "Поиск по коду или названию МКБ-10": "Search ICD-10 by code or name",
  "Вернуть": "Reopen",
  "Вернуть к редактированию": "Reopen for editing",
  "Вернуть к редактированию?": "Reopen for editing?",
  "Да": "Yes",
  "Нет": "No",
  "Диалог недоступен.": "Transcript unavailable.",
  "Диалог сохранён. Нажмите «Обновить заключение».": "Transcript saved. Regenerate the note to apply it.",
  "Если ИИ перепутал, кто врач, а кто пациент, поменяйте роли и обновите заключение.": "If the AI mixed up the doctor and patient, swap roles and regenerate the note.",
  "Есть несохранённые правки": "Unsaved changes",
  "За этот месяц расходов нет": "No usage this month",
  "Загрузить запись для прослушивания": "Load recording for playback",
  "Заключение ещё не создано.": "The note has not been created yet.",
  "Заключение подтверждено": "Note confirmed",
  "Источник разговора": "Transcript source",
  "К списку приёмов": "Back to consultations",
  "Минут аудио": "Audio minutes",
  "Модель": "Model",
  "Нет связи с сервером. Проверьте подключение.": "Cannot reach the server. Check your connection.",
  "Новый черновик заменит текст заключения и памятки, который вы уже исправили.": "The new draft will replace your edited note and patient instructions.",
  "Ожидается JSON-массив кодов": "Expected a JSON array of codes",
  "Отмена": "Cancel",
  "Пароль изменён. Теперь войдите.": "Password changed. Please sign in.",
  "Повторить обработку": "Retry processing",
  "Подготовлено с помощью AqylMed AI. Документ должен быть проверен врачом.": "Prepared with AqylMed AI. A doctor must review this document.",
  "Подтверждение будет снято, действие попадёт в журнал.": "Confirmation will be removed and the action logged.",
  "Пользователь создан": "User created",
  "Последний вход": "Last sign-in",
  "Правки сохранены": "Changes saved",
  "Приём создан из текста, аудио нет.": "This consultation was created from text and has no audio.",
  "Провайдер": "Provider",
  "Проверьте JSON шаблона": "Check the template JSON",
  "Проверьте JSON-массив кодов МКБ-10": "Check the ICD-10 JSON array",
  "Проверьте значения по записи": "Verify values against the recording",
  "Распознавание речи": "Speech recognition",
  "Речь": "Speech",
  "Роли «Врач» и «Пациент» поменялись местами": "Doctor and patient roles swapped",
  "Роль": "Role",
  "Сессия истекла. Войдите снова.": "Session expired. Please sign in again.",
  "Специальность добавлена": "Specialty added",
  "Ссылка подтверждения отправлена": "Verification link sent",
  "Стоимость": "Cost",
  "Тип": "Type",
  "Токены вход / выход": "Input / output tokens",
  "Удалить": "Delete",
  "Удалить аудиозапись?": "Delete audio recording?",
  "Файл будет удалён без возможности восстановления. Текст и заключение сохранятся.": "The file will be permanently deleted. The transcript and note will remain.",
  "Фамилия И. О.": "Patient name",
  "Черновик, не подтверждён": "Unconfirmed draft",
  "Шаблон сохранён": "Template saved",
  "Язык интерфейса": "Interface language",
  "не указано": "not specified",
  "нет": "none",
  "Двухфакторная аутентификация": "Two-factor authentication",
  "SMTP настроен": "SMTP configured",
  "Email-уведомления об изменении пароля": "Password change emails",
  "ffmpeg установлен": "ffmpeg installed",
  "Диаризация (кто говорит)": "Speaker diarization",
  "Месячный лимит расходов": "Monthly spending limit",
  "Удалять аудио после обработки": "Delete audio after processing",
  "Хранение аудио": "Audio retention",
  "Языковая модель": "Language model",
  "без ограничения": "unlimited",
  "выключена, роли определяет языковая модель": "disabled; roles are inferred by the language model",
  "не задан": "not set",
  "Подтверждено:": "Confirmed:",
  "Врач:": "Doctor:",
  "приём": "visit",
  "Импортировано кодов:": "Imported codes:",
  "Удалено записей:": "Deleted recordings:",
  "Лимит не задан": "No budget limit",
  "Врач: Здравствуйте, что вас беспокоит?\nПациент: …": "Doctor: Hello, what brings you in today?\nPatient: …"
});
Object.assign(TRANSLATIONS.kk, {"Уйти без сохранения?": "Өзгерістерді сақтамай шығасыз ба?", "Назад": "Артқа", "Далее": "Келесі", "Сбросить фильтры": "Сүзгілерді тазарту", "Страницы приёмов": "Қабылдау беттері", "Повторить": "Қайталау", "Скачать запись": "Жазбаны жүктеу", "Сохранение…": "Сақталуда…", "Сначала сохраните правки": "Алдымен өзгерістерді сақтаңыз"});
Object.assign(TRANSLATIONS.en, {"Уйти без сохранения?": "Leave without saving changes?", "Назад": "Previous", "Далее": "Next", "Сбросить фильтры": "Reset filters", "Страницы приёмов": "Consultation pages", "Повторить": "Retry", "Скачать запись": "Download recording", "Сохранение…": "Saving…", "Сначала сохраните правки": "Save your changes first"});
function tr(text) {
  const dict = TRANSLATIONS[state.locale || initialLocale];
  return dict?.[text] || (dict?.[text.trim()] ? text.replace(text.trim(), dict[text.trim()]) : text);
}
function rawText(value) { return { __rawText: String(value ?? '') }; }
function setLocale(locale, persist = true) {
  if (!SUPPORTED_LOCALES.includes(locale)) return;
  if (hasUnsavedChanges?.() && !window.confirm(tr('Уйти без сохранения?'))) return;
  state.locale = locale;
  document.documentElement.lang = locale;
  if (persist) localStorage.setItem('aqyl_locale', locale);
  if (state.token) {
    api('/auth/preferences', { method: 'PATCH', body: { locale } })
      .then((user) => { state.user = user; sessionStorage.setItem('aqyl_user', JSON.stringify(user)); })
      .catch((ex) => toast(ex.message, true));
  }
  hasUnsavedChanges = null;
  if (!(location.hash === '#/new' && document.querySelector('.recorder button:not([hidden])[data-recording]'))) route();
}
document.documentElement.lang = initialLocale;
const STATUS = { processing: 'Обработка', draft_created: 'Черновик', confirmed: 'Подтверждено', failed: 'Ошибка' };
const STAGES = {
  queued: 'В очереди',
  diarizing: 'Определяем, кто говорит',
  transcribing: 'Распознаём речь',
  structuring: 'Разбираем диалог и роли',
  generating: 'Готовим заключение и памятку',
};
const AUDIO_STAGES = ['queued', 'diarizing', 'transcribing', 'structuring', 'generating'];
const TEXT_STAGES = ['queued', 'generating'];
const SECTIONS = [
  ['complaints', 'Жалобы'], ['anamnesis', 'Анамнез'], ['symptoms_duration', 'Симптомы и сроки'],
  ['examination', 'Объективные данные'], ['diagnosis', 'Диагноз'], ['treatment_plan', 'План лечения'],
  ['recommendations', 'Рекомендации'],
];

const state = {
  token: sessionStorage.getItem('aqyl_token'),
  user: cachedUser,
  locale: initialLocale,
};
let hasUnsavedChanges = null;
let displayedHash = location.hash || '#/';
let cleanup = null; // таймеры и обработчики текущей страницы

/** Создание DOM без innerHTML: любые данные (в т.ч. речь пациента) вставляются только как текст. */
function h(tag, props, ...kids) {
  const el = document.createElement(tag);
  let value;
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'value') value = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, ['placeholder', 'aria-label', 'title'].includes(k) ? tr(String(v)) : v === true ? '' : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    if (typeof kid === 'object' && Object.hasOwn(kid, '__rawText')) {
      el.append(document.createTextNode(kid.__rawText));
    } else {
      el.append(kid.nodeType ? kid : document.createTextNode(tr(String(kid))));
    }
  }
  if (value !== undefined) el.value = value;
  return el;
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
  const locale = { ru: 'ru-RU', kk: 'kk-KZ', en: 'en-US' }[state.locale] || 'ru-RU';
  return d.toLocaleString(locale, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}
const money = (v) => '$' + Number(v).toFixed(4);

function toast(message, bad) {
  const el = h('div', { class: 'toast' + (bad ? ' bad' : '') }, message);
  document.getElementById('toasts').append(el);
  setTimeout(() => el.remove(), bad ? 7000 : 3500);
}

class ApiError extends Error {
  constructor(status, message, code) { super(message); this.status = status; this.code = code; }
}

async function api(path, { method = 'GET', body, form, raw } = {}) {
  const headers = {};
  if (state.token) headers.Authorization = 'Bearer ' + state.token;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
  let res;
  try { res = await fetch('/api' + path, { method, headers, body: payload }); }
  catch { throw new ApiError(0, 'Нет связи с сервером. Проверьте подключение.'); }
  if (res.status === 401 && state.token) { logout(true); throw new ApiError(401, 'Сессия истекла. Войдите снова.'); }
  if (!res.ok) {
    let msg = 'Ошибка ' + res.status, code;
    try {
      const data = await res.json();
      const d = data.detail;
      if (typeof d === 'string') msg = d;
      else if (d && d.message) { msg = d.message; code = d.code; }
      else if (Array.isArray(d) && d[0]) msg = 'Проверьте поля формы: ' + (d[0].msg || '');
    } catch { /* тело не JSON */ }
    throw new ApiError(res.status, msg, code);
  }
  if (res.status === 204) return null;
  return raw ? res : res.json();
}

function logout(expired) {
  if (!expired && hasUnsavedChanges?.() && !window.confirm(tr('Уйти без сохранения?'))) return;
  hasUnsavedChanges = null;
  state.token = null; state.user = null;
  sessionStorage.removeItem('aqyl_token'); sessionStorage.removeItem('aqyl_user');
  location.hash = '#/login';
  if (expired) toast('Сессия истекла. Войдите снова.', true);
}

function confirmDialog({ title, body, okText = 'Подтвердить', danger }) {
  return new Promise((resolve) => {
    const dlg = h('dialog', null,
      h('h2', null, title), h('div', { class: 'dlg-body' }, body),
      h('div', { class: 'row' },
        h('button', { class: 'btn', onclick: () => dlg.close('no') }, 'Отмена'),
        h('button', { class: 'btn ' + (danger ? 'danger' : 'primary'), onclick: () => dlg.close('yes') }, okText)));
    dlg.addEventListener('close', () => { dlg.remove(); resolve(dlg.returnValue === 'yes'); });
    document.body.append(dlg);
    dlg.showModal();
  });
}

function autosize(t) { t.style.height = 'auto'; t.style.height = t.scrollHeight + 'px'; }

function badge(status) { return h('span', { class: 'badge ' + status }, STATUS[status] || status); }

async function download(path, filename) {
  const res = await api(path, { raw: true });
  const url = URL.createObjectURL(await res.blob());
  const a = h('a', { href: url, download: filename });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/* ============ каркас ============ */
function shell(active, ...content) {
  const navItem = (href, label, key) => h('a', { href, 'aria-current': active === key ? 'page' : null }, label);
  return h('div', null,
    h('header', { class: 'topbar' },
      h('a', { class: 'brand', href: '#/' }, 'Aqyl', h('span', null, 'Med'), ' AI'),
      h('nav', { class: 'nav' },
        navItem('#/', 'Приёмы', 'list'), navItem('#/new', 'Новый приём', 'new'),
        state.user.role === 'admin' ? navItem('#/admin', 'Администрирование', 'admin') : null),
      h('div', { class: 'who' }, rawText(state.user.full_name),
        languagePicker(),
        h('button', { onclick: () => logout(false) }, 'Выйти'))),
    h('main', { class: 'page' }, content));
}

function languagePicker() {
  return h('select', { class: 'language-select', 'aria-label': 'Язык интерфейса', value: state.locale,
    onchange: (e) => { setLocale(e.target.value); e.target.value = state.locale; } },
  ...[['ru', 'Русский'], ['kk', 'Қазақша'], ['en', 'English']].map(([code, label]) =>
    h('option', { value: code }, label)));
}

function mount(node) { $app.replaceChildren(node); window.scrollTo(0, 0); }

/* ============ вход ============ */
function loginPage() {
  const err = h('div', { class: 'error-text', role: 'alert' });
  const email = h('input', { type: 'email', required: true, autocomplete: 'username' });
  const password = h('input', { type: 'password', required: true, autocomplete: 'current-password' });
  const code = h('input', { type: 'text', inputmode: 'numeric', pattern: '\\d{6}', autocomplete: 'one-time-code' });
  const codeField = h('label', { class: 'field', hidden: true }, h('span', null, 'Код из письма'), code);
  const btn = h('button', { class: 'btn primary', type: 'submit' }, 'Войти');
  let challengeId = null;
  const form = h('form', {
    class: 'card narrow',
    onsubmit: async (e) => {
      e.preventDefault(); err.textContent = ''; btn.disabled = true;
      try {
        const data = challengeId
          ? await api('/auth/verify-login', { method: 'POST', body: { challenge_id: challengeId, code: code.value } })
          : await api('/auth/login', { method: 'POST', body: { email: email.value, password: password.value } });
        if (data.requires_2fa) {
          challengeId = data.challenge_id;
          codeField.hidden = false; email.disabled = true; password.disabled = true;
          btn.textContent = tr('Подтвердить'); code.focus();
          toast('Код подтверждения отправлен на email');
          return;
        }
        state.token = data.access_token; state.user = data.user;
        state.locale = localStorage.getItem('aqyl_locale') || data.user.locale || initialLocale;
        data.user.locale = state.locale;
        document.documentElement.lang = state.locale;
        sessionStorage.setItem('aqyl_token', state.token); sessionStorage.setItem('aqyl_user', JSON.stringify(state.user));
        api('/auth/preferences', { method: 'PATCH', body: { locale: state.locale } }).catch((ex) => toast(ex.message, true));
        location.hash = '#/';
      } catch (ex) {
        err.textContent = tr(ex.message);
        if (challengeId && ex.status === 401) { challengeId = null; codeField.hidden = true; email.disabled = false; password.disabled = false; btn.textContent = tr('Войти'); }
      } finally { btn.disabled = false; }
    },
  },
    h('h1', null, 'AqylMed AI'),
    languagePicker(),
    h('p', { class: 'muted' }, 'Помощник врача: превращает запись приёма в черновик заключения.'),
    h('label', { class: 'field' }, h('span', null, 'Email'), email),
    h('label', { class: 'field' }, h('span', null, 'Пароль'), password),
    codeField, h('a', { href: '#/reset' }, 'Забыли пароль?'),
    err, btn);
  mount(h('div', { class: 'page' }, form));
  email.focus();
}

function passwordResetPage() {
  const params = new URLSearchParams((location.hash.split('?')[1] || ''));
  const token = params.get('token');
  const email = h('input', { type: 'email', required: true, autocomplete: 'email' });
  const password = h('input', { type: 'password', required: true, autocomplete: 'new-password' });
  const err = h('div', { class: 'error-text', role: 'alert' });
  const button = h('button', { class: 'btn primary', type: 'submit' }, token ? 'Сохранить пароль' : 'Отправить ссылку');
  const form = h('form', { class: 'card narrow', onsubmit: async (event) => {
    event.preventDefault(); err.textContent = ''; button.disabled = true;
    try {
      if (token) {
        await api('/auth/password-reset/confirm', { method: 'POST', body: { token, new_password: password.value } });
        toast('Пароль изменён. Теперь войдите.');
        location.hash = '#/login';
      } else {
        const result = await api('/auth/password-reset/request', { method: 'POST', body: { email: email.value } });
        toast(result.message);
      }
    } catch (ex) { err.textContent = tr(ex.message); }
    finally { button.disabled = false; }
  } },
  h('h1', null, token ? 'Новый пароль' : 'Восстановление пароля'),
  token
    ? h('label', { class: 'field' }, h('span', null, 'Новый пароль'), password)
    : h('label', { class: 'field' }, h('span', null, 'Email'), email),
  err, button, h('p', null, h('a', { href: '#/login' }, 'Вернуться ко входу')));
  mount(h('div', { class: 'page' }, languagePicker(), form));
}

function verifyEmailPage() {
  const params = new URLSearchParams((location.hash.split('?')[1] || ''));
  const message = h('div', { class: 'muted' }, 'Проверяем ссылку…');
  mount(h('div', { class: 'page' }, h('div', { class: 'card narrow' },
    h('h1', null, 'Подтверждение email'), message,
    h('a', { href: '#/login' }, 'Перейти ко входу'))));
  const token = params.get('token');
  if (!token) { message.textContent = tr('В ссылке отсутствует токен подтверждения.'); return; }
  api('/auth/verify-email?token=' + encodeURIComponent(token), { method: 'POST' })
    .then(() => { message.textContent = tr('Email подтверждён. Теперь войдите в AqylMed.'); })
    .catch((ex) => { message.textContent = ex.message; });
}

/* ============ список приёмов ============ */
async function listPage() {
  const search = h('input', { type: 'search', placeholder: 'Поиск по пациенту или врачу', 'aria-label': 'Поиск по пациенту или врачу' });
  const filter = h('select', { 'aria-label': 'Статус' },
    h('option', { value: '' }, 'Все статусы'),
    ...Object.entries(STATUS).map(([v, l]) => h('option', { value: v }, l)));
  const holder = h('div');
  const count = h('span', { class: 'muted small', role: 'status' });
  let offset = 0, total = 0, timer, debounce, request = 0, disposed = false;
  const limit = 25;
  const previous = h('button', { class: 'btn', disabled: true, onclick: () => { offset = Math.max(0, offset - limit); load(); } }, 'Назад');
  const next = h('button', { class: 'btn', disabled: true, onclick: () => { offset += limit; load(); } }, 'Далее');
  const reset = h('button', { class: 'btn', onclick: () => { search.value = ''; filter.value = ''; changed(); } }, 'Сбросить фильтры');
  mount(shell('list',
    h('div', { class: 'page-head' }, h('h1', null, 'Приёмы'), h('a', { class: 'btn primary', href: '#/new' }, 'Новый приём')),
    h('div', { class: 'toolbar' }, search, filter, reset), holder,
    h('nav', { class: 'pagination', 'aria-label': 'Страницы приёмов' }, count, previous, next)));

  const load = async () => {
    if (disposed) return;
    const version = ++request;
    clearTimeout(timer);
    previous.disabled = true; next.disabled = true;
    holder.setAttribute('aria-busy', 'true');
    count.textContent = tr('Загрузка…');
    try {
      const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
      if (search.value.trim()) q.set('q', search.value.trim());
      if (filter.value) q.set('status', filter.value);
      const data = await api('/consultations?' + q);
      if (disposed || version !== request) return;
      total = data.total;
      if (offset && offset >= total) { offset = Math.max(0, Math.ceil(total / limit) - 1) * limit; return load(); }
      holder.replaceChildren(data.items.length ? table(data.items) : h('div', { class: 'card empty' },
        search.value || filter.value ? 'Ничего не найдено.' : 'Приёмов пока нет. Загрузите запись или вставьте текст разговора.'));
      count.textContent = `${total ? offset + 1 : 0}–${Math.min(offset + data.items.length, total)} / ${total}`;
      previous.disabled = offset === 0; next.disabled = offset + limit >= total;
      if (data.items.some((c) => c.status === 'processing')) timer = setTimeout(load, 4000);
    } catch (ex) {
      if (disposed || version !== request) return;
      count.textContent = '';
      holder.replaceChildren(h('div', { class: 'alert bad' }, ex.message,
        h('button', { class: 'btn', onclick: load }, 'Повторить')));
    } finally { if (!disposed && version === request) holder.removeAttribute('aria-busy'); }
  };
  function changed() { ++request; clearTimeout(timer); clearTimeout(debounce); offset = 0; load(); }
  search.addEventListener('input', () => { ++request; clearTimeout(timer); clearTimeout(debounce); debounce = setTimeout(changed, 300); });
  filter.addEventListener('change', changed);
  cleanup = () => { disposed = true; ++request; clearTimeout(timer); clearTimeout(debounce); };
  load();

  function table(items) {
    return h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
      h('thead', null, h('tr', null, ['Дата приёма', 'Пациент', 'Врач', 'Источник', 'Статус'].map((t) => h('th', null, t)))),
      h('tbody', null, items.map((c) => h('tr', {
        class: 'click', tabindex: '0',
        onclick: () => (location.hash = '#/c/' + c.id),
        onkeydown: (e) => { if (e.key === 'Enter') location.hash = '#/c/' + c.id; },
      },
        h('td', null, rawText(c.consultation_date)), h('td', null, rawText(c.patient_name)), h('td', null, rawText(c.doctor_name)),
        h('td', null, c.source === 'audio' ? 'Аудио' : 'Текст'), h('td', null, badge(c.status)))))));
  }
}

/* ============ новый приём ============ */
function jsonFileInput(onLoad, onError) {
  return h('input', { type: 'file', accept: '.json,application/json', 'aria-label': tr('Загрузить JSON'),
    onchange: async (event) => {
      try {
        const file = event.target.files[0];
        if (!file) return;
        if (file.size > 10 * 1024 * 1024) throw new Error(tr('Файл больше 10 МБ'));
        onLoad(JSON.parse((await file.text()).replace(/^\uFEFF/, '')));
      } catch (ex) { onError(ex instanceof SyntaxError ? tr('Некорректный JSON') : ex.message); }
    } });
}
function exampleDownload(name, data) {
  return h('button', { type: 'button', class: 'btn', onclick: () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const link = h('a', { href: url, download: name }); link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } }, 'Скачать пример JSON');
}
function documentTypePicker() {
  return h('select', { 'aria-label': tr('Тип документа') },
    ...[['initial', 'Первичный приём'], ['examination', 'Осмотр'], ['discharge', 'Выписка']]
      .map(([value, label]) => h('option', { value }, label)));
}
function newPage() {
  let mode = 'audio', recorded = null, recorder = null, stream = null, tick = null;
  let elapsedMs = 0, activeSince = 0;
  const documentType = documentTypePicker();
  const patient = h('input', { type: 'text', required: true, maxlength: '255', placeholder: 'Фамилия И. О.' });
  const date = h('input', { type: 'date', required: true, value: new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10) });
  const fileInput = h('input', { type: 'file', accept: 'audio/*,.mp3,.m4a,.wav,.ogg,.webm,.flac,.mp4' });
  const text = h('textarea', { rows: '12', placeholder: 'Врач: Здравствуйте, что вас беспокоит?\nПациент: …' });
  const consent = h('input', { type: 'checkbox' });
  const err = h('div', { class: 'error-text', role: 'alert' });
  const submit = h('button', { class: 'btn primary', type: 'submit' }, 'Создать черновик заключения');
  const modeBox = h('div');
  const seg = h('div', { class: 'segmented', role: 'group', 'aria-label': 'Источник разговора' });

  const recLabel = h('span', { class: 'muted' }, 'Запись с микрофона');
  const dot = h('span', { class: 'rec-dot' });
  const recBtn = h('button', { type: 'button', class: 'btn', onclick: toggleRecord }, 'Начать запись');
  const pauseBtn = h('button', { type: 'button', class: 'btn', hidden: true, onclick: pauseRecord }, 'Пауза');
  const preview = h('audio', { controls: true, hidden: true });
  const saveAudio = h('a', { class: 'btn', hidden: true }, 'Скачать запись');

  function drawMode() {
    seg.replaceChildren(
      h('button', { type: 'button', 'aria-pressed': mode === 'audio', onclick: () => { mode = 'audio'; drawMode(); } }, 'Аудиозапись'),
      h('button', { type: 'button', 'aria-pressed': mode === 'text', onclick: () => { if (recorder && recorder.state !== 'inactive') recorder.stop(); mode = 'text'; drawMode(); } }, 'Готовый текст'));
    modeBox.replaceChildren(mode === 'audio'
      ? h('div', null,
        h('div', { class: 'recorder' }, dot, recLabel, recBtn, pauseBtn),
        preview, saveAudio,
        h('label', { class: 'field' }, h('span', null, 'Или загрузите файл'), fileInput,
          h('div', { class: 'help' }, 'WAV, MP3, M4A, OGG, FLAC, WebM. Обработка занимает 1–3 минуты.')),
        h('label', { class: 'field' }, h('span', null, 'Согласие'),
          h('label', null, consent, ' Пациент дал согласие на запись и обработку разговора')))
      : h('label', { class: 'field' }, h('span', null, 'Текст разговора'), text,
        h('div', { class: 'help' }, 'Каждую реплику с новой строки, с пометкой «Врач:» или «Пациент:».')));
  }

  async function toggleRecord() {
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
      pauseBtn.hidden = true;
      return;
    }
    if (!navigator.mediaDevices || !window.MediaRecorder) { err.textContent = tr('Браузер не поддерживает запись. Загрузите готовый файл.'); return; }
    recBtn.disabled = true;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch { err.textContent = tr('Нет доступа к микрофону. Разрешите его в браузере (нужен HTTPS или localhost).'); return; }
    finally { recBtn.disabled = false; }
    recorded = null; fileInput.value = ''; saveAudio.hidden = true;
    err.textContent = '';
    const chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      clearInterval(tick); stream.getTracks().forEach((t) => t.stop()); dot.classList.remove('live');
      pauseBtn.hidden = true;
      submit.disabled = false;
      delete pauseBtn.dataset.recording;
      if (preview.src) URL.revokeObjectURL(preview.src);
      const type = recorder.mimeType || 'audio/webm';
      const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
      recorded = new File(chunks, 'recording.' + ext, { type });
      preview.src = URL.createObjectURL(recorded); preview.hidden = false;
      saveAudio.href = preview.src; saveAudio.download = recorded.name; saveAudio.hidden = false;
      recBtn.textContent = tr('Записать заново'); recLabel.textContent = tr('Запись готова');
    };
    recorder.start(); pauseBtn.dataset.recording = 'true'; dot.classList.add('live'); recBtn.textContent = tr('Остановить');
    elapsedMs = 0; activeSince = Date.now();
    pauseBtn.textContent = tr('Пауза');
    submit.disabled = true;
    tick = setInterval(() => {
      const s = Math.floor((elapsedMs + (recorder.state === 'recording' ? Date.now() - activeSince : 0)) / 1000);
      recLabel.textContent = `${tr(recorder.state === 'paused' ? 'Запись приостановлена' : 'Идёт запись')} ${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
    }, 500);
    pauseBtn.hidden = false;
  }

  function pauseRecord() {
    if (!recorder) return;
    if (recorder.state === 'recording') {
      elapsedMs += Date.now() - activeSince;
      recorder.pause();
      dot.classList.remove('live');
      pauseBtn.textContent = tr('Продолжить');
      recLabel.textContent = tr('Запись приостановлена');
    } else if (recorder.state === 'paused') {
      activeSince = Date.now();
      recorder.resume();
      dot.classList.add('live');
      pauseBtn.textContent = tr('Пауза');
    }
  }

  const form = h('form', {
    class: 'card',
    onsubmit: async (e) => {
      e.preventDefault(); err.textContent = ''; submit.disabled = true;
      try {
        let res;
        if (mode === 'audio') {
          const file = fileInput.files[0] || recorded;
          if (!file) throw new Error('Запишите разговор или выберите файл.');
          if (!consent.checked) throw new Error('Подтвердите согласие пациента на запись.');
          const fd = new FormData();
          fd.append('document_type', documentType.value);
          fd.append('patient_name', patient.value); fd.append('consultation_date', date.value);
          fd.append('consent_confirmed', 'true'); fd.append('file', file, file.name);
          res = await api('/consultations/audio', { method: 'POST', form: fd });
        } else {
          res = await api('/consultations/text', { method: 'POST',
            body: { document_type: documentType.value, patient_name: patient.value, consultation_date: date.value, dialogue_text: text.value } });
        }
        location.hash = '#/c/' + res.id;
      } catch (ex) { err.textContent = tr(ex.message); submit.disabled = false; }
    },
  },
    seg,
    h('div', { class: 'grid-2' },
      h('label', { class: 'field' }, h('span', null, 'Пациент'), patient),
      h('label', { class: 'field' }, h('span', null, 'Дата приёма'), date)),
    h('label', { class: 'field' }, h('span', null, 'Тип документа'), documentType),
    modeBox, err, submit);
  drawMode();
  cleanup = () => {
    clearInterval(tick);
    if (recorder && recorder.state !== 'inactive') { recorder.onstop = null; recorder.stop(); }
    if (stream) stream.getTracks().forEach((t) => t.stop());
    if (preview.src) URL.revokeObjectURL(preview.src);
  };
  mount(shell('new',
    h('div', { class: 'page-head' }, h('h1', null, 'Новый приём')),
    h('div', null, form),
    h('p', { class: 'muted small' }, 'Результат — черновик. Он не попадает в карту, пока вы его не проверите и не подтвердите.')));
}

/* ============ страница приёма ============ */
async function detailPage(id) {
  if (cleanup) { cleanup(); cleanup = null; }
  mount(shell('', h('div', { class: 'muted' }, 'Загрузка…')));
  let c, templateFields = {};
  try {
    c = await api('/consultations/' + id);
    const locale = c.output_locale || state.locale || 'ru';
    templateFields = c.template_fields || {};
  }
  catch (ex) { mount(shell('', h('div', { class: 'alert bad' }, ex.message), h('a', { href: '#/' }, 'К списку приёмов'))); return; }
  if (c.status === 'processing') return processingView(c);
  renderDetail(c, templateFields);
}

function processingView(c) {
  const order = c.source === 'audio' ? AUDIO_STAGES : TEXT_STAGES;
  const list = h('ul', { class: 'stages' });
  const draw = (stage) => {
    const idx = order.indexOf(stage);
    list.replaceChildren(...order.map((s, i) => h('li', { class: i < idx ? 'done' : i === idx ? 'now' : '' }, STAGES[s])));
  };
  draw(c.progress_stage);
  mount(shell('',
    h('div', { class: 'page-head' }, h('div', { class: 'title-row' }, h('h1', null, rawText(c.patient_name)), badge('processing'))),
    h('div', { class: 'card' }, h('h2', null, 'Готовим черновик'),
      h('p', { class: 'muted' }, 'Страницу можно закрыть — обработка продолжится на сервере.'), list)));
  let stopped = false;
  const poll = async () => {
    if (stopped) return;
    try {
      const s = await api(`/consultations/${c.id}/status`);
      if (s.status !== 'processing') { detailPage(c.id); return; }
      draw(s.progress_stage);
    } catch (ex) { if (ex.status === 404) return; }
    if (!stopped) setTimeout(poll, 2000);
  };
  setTimeout(poll, 1500);
  cleanup = () => { stopped = true; };
}

function parseTurns(textValue) {
  const turns = [];
  for (const line of (textValue || '').split('\n')) {
    const m = line.match(/^\s*(Врач|Пациент|Неизвестный)\s*:\s*(.*)$/);
    if (m) turns.push({ role: m[1], text: m[2] });
    else if (line.trim()) { if (turns.length) turns[turns.length - 1].text += ' ' + line.trim(); else turns.push({ role: '', text: line.trim() }); }
  }
  return turns;
}

function renderDetail(c, templateFields = {}) {
  if (cleanup) { cleanup(); cleanup = null; }
  const editable = c.can_edit;
  const doc = c.document || {};
  const fields = {}; // имя -> textarea
  let memoArea = null;
  let dirty = false, editVersion = 0, saving = null;
  let dialogueDraft = c.dialogue_text || "";
  let tab = 'dialogue';
  let audioUrl = null;

  const markDirty = () => { ++editVersion; dirty = true; saveBtn.disabled = !!saving; saveBtn.textContent = tr(saving ? 'Сохранение…' : 'Сохранить правки'); };
  const area = (value, onInput) => {
    const t = h('textarea', { rows: '2', oninput: () => { autosize(t); markDirty(); onInput && onInput(); } }, value || '');
    t.value = value || '';
    requestAnimationFrame(() => autosize(t));
    return t;
  };

  const flagged = new Set();
  if (editable && doc.diagnosis && /не указан/i.test(doc.diagnosis)) flagged.add('diagnosis');

  const sheetSections = c.document ? SECTIONS.map(([key, fallbackTitle]) => {
    const title = rawText(templateFields[key] || TRANSLATIONS[c.output_locale]?.[fallbackTitle] || fallbackTitle);
    const body = editable
      ? (fields[key] = area(doc[key]))
      : h('div', { class: 'body' }, rawText(doc[key] || 'не указано'));
    const codeControl = key === 'diagnosis' ? (() => {
      if (!editable) return h('div', { class: 'body' }, doc.diagnosis_code || '');
      const listId = 'icd10-options-' + c.id;
      const code = h('input', { type: 'search', list: listId, placeholder: 'Поиск по коду или названию МКБ-10',
        value: doc.diagnosis_code || '', oninput: searchCodes });
      fields.diagnosis_code = code;
      const options = h('datalist', { id: listId });
      async function searchCodes() {
        if (code.value.trim().length < 2) { options.replaceChildren(); return; }
        try {
          const results = await api('/catalog/icd10?q=' + encodeURIComponent(code.value.trim()) +
            '&locale=' + encodeURIComponent(c.output_locale || state.locale || 'ru'));
          options.replaceChildren(...results.map((r) => h('option', { value: r.code, label: r.name })));
        } catch (ex) { toast(ex.message, true); }
      }
      code.addEventListener('input', markDirty);
      return h('label', { class: 'field icd-field' },
        h('span', null, templateFields.diagnosis_code || 'Код МКБ-10'), code, options,
        h('div', { class: 'help' }, 'Введите код или название, выберите код из справочника.'));
    })() : null;
    return h('div', { class: 'section' + (flagged.has(key) ? ' flag' : '') },
      h('h3', null, title), body, codeControl);
  }) : [];
  if (c.document) {
    const miss = editable ? (fields.missing_information = area((doc.missing_information || []).join('\n'))) :
      h('div', { class: 'body' }, rawText((doc.missing_information || []).join('\n') || 'нет'));
    sheetSections.push(h('div', { class: 'section' + (editable && (doc.missing_information || []).length ? ' flag' : '') },
      h('h3', null, 'Требует уточнения'), miss,
      editable ? h('div', { class: 'help' }, 'По одному пункту в строке.') : null));
  }

  const memoBlock = c.memo ? h('div', { class: 'memo' }, h('h2', null, 'Памятка пациенту'),
    editable ? (memoArea = area(c.memo.memo_text)) : h('div', { class: 'body' }, rawText(c.memo.memo_text))) : null;
  if (memoBlock && !editable) memoBlock.lastChild.style.whiteSpace = 'pre-wrap';

  const sheet = h('article', { class: 'sheet' },
    h('div', { class: 'sheet-head' },
      h('div', null, h('h1', null, rawText(TRANSLATIONS[c.output_locale]?.['Медицинское заключение'] || 'Медицинское заключение')), h('div', { class: 'muted' }, ({initial: 'Первичный приём', examination: 'Осмотр', discharge: 'Выписка'})[c.document_type] || 'Первичный приём'),
        h('div', { class: 'sheet-meta' }, h('b', null, rawText(c.patient_name)), ' — ' + tr('приём') + ' ', rawText(c.consultation_date))),
        h('div', { class: 'sheet-meta' }, 'Врач: ', h('b', null, rawText(c.doctor_name)), h('br'),
        c.status === 'confirmed' ? `${tr('Подтверждено:')} ${c.confirmed_by || ''}, ${fmtDate(c.confirmed_at)}` : 'Черновик, не подтверждён')),
    sheetSections, memoBlock,
    h('p', { class: 'disclaimer' }, 'Подготовлено с помощью AqylMed AI. Документ должен быть проверен врачом.'));

  /* ---- панель действий ---- */
  const saveBtn = h('button', { class: 'btn', disabled: true, onclick: save }, 'Сохранено');
  const confirmBtn = h('button', { class: 'btn ok', onclick: confirmDoc }, 'Подтвердить заключение');
  const actions = h('div', { class: 'actionbar' },
    h('a', { class: 'btn', href: '#/' }, 'К списку'),
    editable ? [saveBtn, confirmBtn] : null,
    c.status === 'confirmed' ? h('button', { class: 'btn', onclick: reopen }, 'Вернуть к редактированию') : null,
    h('span', { class: 'spacer' }),
    c.document ? [
      h('button', { class: 'btn', onclick: async () => { if (!await prepareOutput()) return; download(`/consultations/${c.id}/export?format=docx`, `zaklyuchenie_${c.id}.docx`).catch((e) => toast(e.message, true)); } }, 'Скачать Word'),
      h('button', { class: 'btn', onclick: async () => { if (await prepareOutput()) window.print(); } }, 'Печать'),
    ] : null);

  async function prepareOutput() {
    if (dirty || saving) {
      if (!await save(true) || dirty) { toast('Сначала сохраните правки', true); return false; }
    }
    return true;
  }

  function save(silent) {
    if (saving) return saving;
    saveBtn.disabled = true; saveBtn.textContent = tr('Сохранение…');
    const version = editVersion;
    const memoValue = memoArea?.value;
    const dialogueValue = dialogueDraft;
    saving = Promise.resolve().then(async () => {
    try {
      let updated = c;
      const body = {};
      for (const [key] of SECTIONS) if (fields[key] && fields[key].value !== (doc[key] || '')) body[key] = fields[key].value;
      if (fields.diagnosis_code && fields.diagnosis_code.value !== (doc.diagnosis_code || '')) {
        body.diagnosis_code = fields.diagnosis_code.value;
      }
      if (fields.missing_information) {
        const list = fields.missing_information.value.split('\n').map((s) => s.trim()).filter(Boolean);
        if (list.join('\n') !== (doc.missing_information || []).join('\n')) body.missing_information = list;
      }
      if (Object.keys(body).length) updated = await api(`/consultations/${c.id}/document`, { method: 'PUT', body });
      if (memoArea && memoValue !== c.memo.memo_text) updated = await api(`/consultations/${c.id}/memo`, { method: 'PUT', body: { memo_text: memoValue } });
      if (dialogueValue !== (c.dialogue_text || '')) updated = await api(`/consultations/${c.id}/dialogue`, { method: 'PUT', body: { dialogue_text: dialogueValue } });
      dirty = editVersion !== version;
      Object.assign(c, updated); Object.assign(doc, updated.document || {}); if (c.memo && updated.memo) c.memo.memo_text = updated.memo.memo_text;
      if (silent !== true) toast('Правки сохранены');
      return true;
    } catch (ex) { toast(ex.message, true); return false; }
    finally {
      saving = null; saveBtn.disabled = !dirty;
      saveBtn.textContent = tr(dirty ? 'Сохранить правки' : 'Сохранено');
    }
    });
    return saving;
  }

  async function confirmDoc() {
    const warnings = (doc.validation_warnings || []);
    const ok = await confirmDialog({
      title: 'Подтвердить заключение?',
      okText: 'Подтверждаю',
      body: h('div', null,
        h('p', null, 'Вы подтверждаете, что проверили текст и несёте ответственность за его содержание.'),
        warnings.length ? h('div', { class: 'alert warn' }, `Остались непроверенные значения (${warnings.length}). Откройте вкладку «Проверка».`) : null),
    });
    if (!ok) return;
    if (!(await prepareOutput())) return;
    try { renderDetail(await api(`/consultations/${c.id}/confirm`, { method: 'POST' }), templateFields); toast('Заключение подтверждено'); }
    catch (ex) { toast(ex.message, true); }
  }
  async function reopen() {
    if (!(await confirmDialog({ title: 'Вернуть к редактированию?', body: 'Подтверждение будет снято, действие попадёт в журнал.', okText: 'Вернуть' }))) return;
    try { renderDetail(await api(`/consultations/${c.id}/reopen`, { method: 'POST' }), templateFields); } catch (ex) { toast(ex.message, true); }
  }

  async function regenerate() {
    const run = async (confirmOverwrite) => api(`/consultations/${c.id}/regenerate`, { method: 'POST', body: { confirm_overwrite: confirmOverwrite } });
    try {
      if (saving) await saving;
      if (dirty && !(await confirmDialog({ title: 'Заменить правки?', body: 'Новый черновик заменит текст заключения и памятки, который вы уже исправили.', okText: 'Заменить', danger: true }))) return;
      if (dialogueDraft !== (c.dialogue_text || '')) {
        const updated = await api(`/consultations/${c.id}/dialogue`, { method: 'PUT', body: { dialogue_text: dialogueDraft } });
        c.dialogue_text = updated.dialogue_text;
      }
      try { await run(dirty); }
      catch (ex) {
        if (ex.code !== 'edits_would_be_lost') throw ex;
        if (!(await confirmDialog({ title: 'Заменить правки?', body: 'Новый черновик заменит текст заключения и памятки, который вы уже исправили.', okText: 'Заменить', danger: true }))) return;
        await run(true);
      }
      dirty = false;
      detailPage(c.id);
    } catch (ex) { toast(ex.message, true); }
  }

  /* ---- боковая панель ---- */
  const panel = h('div', { class: 'tabpanel' });
  const tabs = h('div', { class: 'tabs', role: 'tablist' });
  const warningCount = (doc.validation_warnings || []).length;
  function drawTabs() {
    const mk = (key, label, count) => h('button', { role: 'tab', 'aria-selected': tab === key, onclick: () => { tab = key; drawTabs(); drawPanel(); } },
      label, count ? h('span', { class: 'tab-count' }, count) : null);
    tabs.replaceChildren(mk('dialogue', 'Диалог'), mk('audio', 'Запись'), mk('check', 'Проверка', warningCount || null));
  }

  function drawPanel() {
    if (tab === 'dialogue') panel.replaceChildren(dialogueTab());
    else if (tab === 'audio') panel.replaceChildren(audioTab());
    else panel.replaceChildren(checkTab());
  }

  function dialogueTab() {
    const wrap = h('div', { class: 'dialogue' });
    const canEditDialogue = c.status === 'draft_created' || c.status === 'failed';
    const view = h('div');
    const drawView = () => view.replaceChildren(...(parseTurns(c.dialogue_text).length
      ? parseTurns(c.dialogue_text).map((t) => h('div', { class: 'turn' + (t.role === 'Врач' ? ' doc' : '') }, t.role ? h('b', null, t.role) : null, rawText(t.text)))
      : [h('p', { class: 'muted' }, 'Диалог недоступен.')]));
    drawView();
    wrap.append(view);
    if (canEditDialogue && c.dialogue_text) {
      const edit = h('textarea', { rows: '14', oninput: () => { dialogueDraft = edit.value; markDirty(); } }); edit.value = dialogueDraft; edit.hidden = true;
      const btnEdit = h('button', { class: 'btn', onclick: () => { edit.hidden = !edit.hidden; view.hidden = !edit.hidden; btnEdit.textContent = edit.hidden ? 'Править текст' : 'Закрыть редактор'; btnSave.hidden = edit.hidden; } }, 'Править текст');
      const btnSave = h('button', { class: 'btn', hidden: true, onclick: async () => {
        try { if (!await save(true)) return; drawView(); edit.hidden = true; view.hidden = false; btnSave.hidden = true; btnEdit.textContent = tr('Править текст'); toast('Диалог сохранён. Нажмите «Обновить заключение».'); }
        catch (ex) { toast(ex.message, true); } } }, 'Сохранить диалог');
      const btnSwap = h('button', { class: 'btn', onclick: async () => {
        try { if (!await prepareOutput()) return; Object.assign(c, await api(`/consultations/${c.id}/swap-roles`, { method: 'POST' })); dialogueDraft = c.dialogue_text; edit.value = dialogueDraft; drawView(); toast('Роли «Врач» и «Пациент» поменялись местами'); }
        catch (ex) { toast(ex.message, true); } } }, 'Поменять роли');
      wrap.append(edit, h('div', { class: 'toolbar' }, btnEdit, btnSave, btnSwap),
        h('div', { class: 'help' }, 'Если ИИ перепутал, кто врач, а кто пациент, поменяйте роли и обновите заключение.'),
        h('button', { class: 'btn primary', onclick: regenerate }, 'Обновить заключение по диалогу'));
    }
    return wrap;
  }

  function audioTab() {
    const box = h('div');
    if (!c.audio.available) {
      box.append(h('p', { class: 'muted' }, c.source === 'audio'
        ? `Запись удалена${c.audio.deleted_at ? ' ' + fmtDate(c.audio.deleted_at) : ''} (срок хранения или по запросу).`
        : 'Приём создан из текста, аудио нет.'));
      return box;
    }
    const player = h('audio', { controls: true, preload: 'none' });
    const load = h('button', { class: 'btn', onclick: async () => {
      load.disabled = true;
      try { const res = await api(`/consultations/${c.id}/audio`, { raw: true }); audioUrl = URL.createObjectURL(await res.blob()); player.src = audioUrl; player.play(); load.hidden = true; }
      catch (ex) { toast(ex.message, true); load.disabled = false; } } }, 'Загрузить запись для прослушивания');
    box.append(h('p', { class: 'muted small' }, `Длительность: ${c.audio.duration_seconds ? Math.round(c.audio.duration_seconds / 60 * 10) / 10 + ' мин' : '—'}. Каждое прослушивание фиксируется в журнале.`), player, load);
    if (c.status !== 'processing') {
      box.append(h('div', null, h('button', { class: 'btn danger', onclick: async () => {
        if (!(await confirmDialog({ title: 'Удалить аудиозапись?', body: 'Файл будет удалён без возможности восстановления. Текст и заключение сохранятся.', okText: 'Удалить', danger: true }))) return;
        try { await api(`/consultations/${c.id}/audio`, { method: 'DELETE' }); c.audio.available = false; c.audio.deleted_at = new Date().toISOString(); drawPanel(); toast('Запись удалена'); }
        catch (ex) { toast(ex.message, true); } } }, 'Удалить запись')));
    }
    return box;
  }

  function checkTab() {
    const box = h('div');
    const w = doc.validation_warnings || [];
    box.append(w.length
      ? h('div', { class: 'alert warn' }, h('b', null, 'Проверьте значения по записи'), h('ul', null, w.map((x) => h('li', null, x))))
      : h('div', { class: 'alert ok' }, 'Все числа и дозировки из заключения найдены в диалоге.'));
    if (!c.dialogue_text) box.append(h('p', { class: 'muted' }, 'Нет диалога для сверки.'));
    if ((doc.missing_information || []).length) box.append(h('div', { class: 'alert info' }, h('b', null, 'ИИ не нашёл в разговоре'), h('ul', null, doc.missing_information.map((x) => h('li', null, rawText(x))))));
    if (c.transcript_notes) box.append(h('div', { class: 'alert info' }, h('b', null, 'Заметки по расшифровке'), h('div', { class: 'small' }, c.transcript_notes.split('\n').map((l) => h('div', null, rawText(l))))));
    box.append(h('p', { class: 'muted small' }, 'Проверка автоматическая и не заменяет вашу: она ищет только числа с единицами измерения.'));
    return box;
  }

  /* ---- сборка ---- */
  const banner = c.status === 'failed'
    ? h('div', { class: 'alert bad banner' }, h('b', null, 'Обработка не удалась. '), c.error_message || '', ' ',
      h('button', { class: 'btn', onclick: regenerate }, 'Повторить обработку'))
    : null;

  const side = h('aside', { class: 'side' }, tabs, panel);
  drawTabs(); drawPanel();
  const saveShortcut = (event) => { if (editable && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); if (dirty) save(); } };
  window.addEventListener('keydown', saveShortcut);
  hasUnsavedChanges = () => dirty || !!saving;
  cleanup = () => { if (audioUrl) URL.revokeObjectURL(audioUrl); window.onbeforeunload = null; window.removeEventListener('keydown', saveShortcut); };
  window.onbeforeunload = () => (dirty ? 'Есть несохранённые правки' : undefined);

  mount(shell('',
    h('div', { class: 'page-head' }, h('div', { class: 'title-row' }, h('h1', null, rawText(c.patient_name)), badge(c.status))),
    banner,
    c.document
      ? h('div', null, h('div', { class: 'detail' }, sheet, side), actions)
      : h('div', { class: 'detail' }, h('div', { class: 'card' }, 'Заключение ещё не создано.'), side)));
}

/* ============ администрирование ============ */
async function adminPage() {
  let tab = 'usage';
  const body = h('div');
  const tabs = h('div', { class: 'segmented' });
  const draw = () => {
    tabs.replaceChildren(...[['usage', 'Расходы'], ['users', 'Пользователи'], ['catalog', 'Справочники'],
      ['audit', 'Журнал'], ['system', 'Система']]
      .map(([k, l]) => h('button', { 'aria-pressed': tab === k, onclick: () => { tab = k; draw(); } }, l)));
    body.replaceChildren(h('div', { class: 'muted' }, 'Загрузка…'));
    ({ usage: usageTab, users: usersTab, catalog: catalogTab, audit: auditTab, system: systemTab })[tab]().then((n) => body.replaceChildren(n))
      .catch((ex) => body.replaceChildren(h('div', { class: 'alert bad' }, ex.message)));
  };
  mount(shell('admin', h('div', { class: 'page-head' }, h('h1', null, 'Администрирование')), tabs, body));
  draw();

  async function usageTab() {
    const month = h('input', { type: 'text', value: new Date().toISOString().slice(0, 7), pattern: '\\d{4}-\\d{2}', 'aria-label': 'Месяц ГГГГ-ММ' });
    const holder = h('div');
    const load = async () => {
      const s = await api('/admin/usage?month=' + encodeURIComponent(month.value));
      const max = Math.max(...s.by_day.map((d) => d.cost_usd), 0.000001);
      holder.replaceChildren(
        h('div', { class: 'kpis' },
          h('div', { class: 'kpi' }, h('div', { class: 'muted small' }, 'Расходы за месяц'), h('div', { class: 'v' }, money(s.total_cost_usd)),
            s.budget_usd ? h('div', { class: 'bar' + (s.budget_used_percent >= 90 ? ' hot' : '') }, h('i', { 'data-w': Math.min(100, s.budget_used_percent) })) : null,
            h('div', { class: 'small muted' }, s.budget_usd ? `Лимит $${s.budget_usd.toFixed(2)}, использовано ${s.budget_used_percent}%` : 'Лимит не задан')),
          h('div', { class: 'kpi' }, h('div', { class: 'muted small' }, 'Обработано приёмов'), h('div', { class: 'v' }, s.consultations_processed)),
          h('div', { class: 'kpi' }, h('div', { class: 'muted small' }, 'Средняя стоимость приёма'), h('div', { class: 'v' }, s.avg_cost_per_consultation_usd == null ? '—' : money(s.avg_cost_per_consultation_usd)))),
        h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
          h('thead', null, h('tr', null, ['Тип', 'Провайдер', 'Модель', 'Минут аудио', 'Токены вход / выход', 'Стоимость'].map((t) => h('th', null, t)))),
          h('tbody', null, s.by_model.length ? s.by_model.map((m) => h('tr', null, h('td', null, m.kind === 'stt' ? 'Речь' : 'Текст'), h('td', null, m.provider), h('td', null, m.model),
            h('td', null, m.audio_minutes || '—'), h('td', null, m.kind === 'llm' ? `${m.input_tokens} / ${m.output_tokens}` : '—'), h('td', null, money(m.cost_usd))))
            : h('tr', null, h('td', { colspan: '6', class: 'empty' }, 'За этот месяц расходов нет'))))),
        s.by_day.length ? h('p', { class: 'muted small' }, 'По дням: ' + s.by_day.map((d) => `${d.day.slice(8)}-е — ${money(d.cost_usd)}`).join('; ')) : null);
      holder.querySelectorAll('i[data-w]').forEach((i) => { i.style.width = i.dataset.w + '%'; });
      void max;
    };
    month.addEventListener('change', () => load().catch((e) => toast(e.message, true)));
    await load();
    return h('div', null, h('label', { class: 'field' }, h('span', null, 'Месяц (ГГГГ-ММ)'), month), holder);
  }

  async function usersTab() {
    const [users, specialties] = await Promise.all([api('/admin/users'), api('/catalog/specialties')]);
    const err = h('div', { class: 'error-text', role: 'alert' });
    const f = { email: h('input', { type: 'email', required: true }), name: h('input', { type: 'text', required: true }),
      pass: h('input', { type: 'password', required: true, autocomplete: 'new-password' }),
      role: h('select', null, h('option', { value: 'doctor' }, 'Врач'), h('option', { value: 'admin' }, 'Администратор')),
      specialty: h('select', null, h('option', { value: '' }, 'Не выбрана'),
        ...specialties.map((s) => h('option', { value: String(s.id) }, rawText(s[`name_${state.locale}`] || s.name_ru)))) };
    const form = h('form', { class: 'card', onsubmit: async (e) => {
      e.preventDefault(); err.textContent = '';
      try { await api('/admin/users', { method: 'POST', body: { email: f.email.value, full_name: f.name.value, password: f.pass.value, role: f.role.value, specialty_id: f.specialty.value ? Number(f.specialty.value) : null } }); toast('Пользователь создан'); draw(); }
      catch (ex) { err.textContent = tr(ex.message); } } },
      h('h2', null, 'Новый пользователь'),
      h('div', { class: 'inline-form' }, h('label', { class: 'field' }, h('span', null, 'Email'), f.email), h('label', { class: 'field' }, h('span', null, 'ФИО'), f.name),
        h('label', { class: 'field' }, h('span', null, 'Пароль'), f.pass), h('label', { class: 'field' }, h('span', null, 'Роль'), f.role),
        h('label', { class: 'field' }, h('span', null, 'Специальность'), f.specialty),
        h('button', { class: 'btn primary', type: 'submit' }, 'Создать')), err);
    const table = h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
      h('thead', null, h('tr', null, ['Email', 'ФИО', 'Роль', 'Специальность', 'Email подтверждён', 'Последний вход', ''].map((t) => h('th', null, t)))),
      h('tbody', null, users.map((u) => h('tr', null, h('td', null, u.email), h('td', null, u.full_name), h('td', null, u.role === 'admin' ? 'Администратор' : 'Врач'),
        h('td', null, h('select', { value: String(u.specialty_id || ''), 'aria-label': tr('Специальность'), onchange: async (event) => {
          try { await api('/admin/users/' + u.id, { method: 'PATCH', body: { specialty_id: event.target.value ? Number(event.target.value) : null } }); toast('Сохранено'); }
          catch (ex) { event.target.value = String(u.specialty_id || ''); toast(ex.message, true); }
        } }, h('option', { value: '' }, 'Не выбрана'), ...specialties.map((s) => h('option', { value: String(s.id) }, rawText(s[`name_${state.locale}`] || s.name_ru))))),
        h('td', null, u.email_verified ? 'Да' : h('button', { class: 'btn', onclick: async () => {
          try { await api(`/admin/users/${u.id}/verification`, { method: 'POST' }); toast('Ссылка подтверждения отправлена'); }
          catch (ex) { toast(ex.message, true); } } }, 'Отправить ссылку')),
        h('td', null, fmtDate(u.last_login_at) || '—'),
        h('td', null, h('button', { class: 'btn' + (u.is_active ? ' danger' : ''), onclick: async () => {
          try { await api('/admin/users/' + u.id, { method: 'PATCH', body: { is_active: !u.is_active } }); draw(); } catch (ex) { toast(ex.message, true); } } }, u.is_active ? 'Отключить' : 'Включить')))))));
    return h('div', { class: 'stack' }, form, table);
  }

  async function catalogTab() {
    const specialties = await api('/catalog/specialties');
    const notice = h('div', { class: 'error-text', role: 'alert' });
    const specialtyForm = h('form', { class: 'card', onsubmit: async (event) => {
      event.preventDefault(); notice.textContent = '';
      const fields = specialtyForm.querySelectorAll('input');
      try {
        await api('/catalog/specialties', { method: 'POST', body: {
          name_ru: fields[0].value, name_kk: fields[1].value, name_en: fields[2].value,
        } });
        toast('Специальность добавлена'); draw();
      } catch (ex) { notice.textContent = tr(ex.message); }
    } },
    h('h2', null, 'Справочник специальностей'),
    ...[['Название на русском', 'name_ru'], ['Қазақша атауы', 'name_kk'], ['Name in English', 'name_en']]
      .map(([label, name]) => h('label', { class: 'field' }, h('span', null, label), h('input', { type: 'text', name, required: name === 'name_ru' }))),
    h('button', { class: 'btn primary', type: 'submit' }, 'Добавить специальность'),
    specialties.length ? h('ul', null, specialties.map((s) => h('li', null, `${s.name_ru} / ${s.name_kk || '—'} / ${s.name_en || '—'}`))) : null);

    const specialtyJson = h('textarea', { rows: '5', 'aria-label': tr('Справочник специальностей') });
    const specialtyImport = h('form', { class: 'card', onsubmit: async (event) => {
      event.preventDefault(); notice.textContent = '';
      try {
        await api('/catalog/specialties', { method: 'PUT', body: JSON.parse(specialtyJson.value) });
        toast('Сохранено'); draw();
      } catch (ex) { notice.textContent = tr(ex.message); }
    } }, h('h2', null, 'Загрузить специальности'),
      jsonFileInput((data) => { specialtyJson.value = JSON.stringify(data, null, 2); }, (error) => { notice.textContent = error; }),
      exampleDownload('specialties.json', [{ name_ru: 'Название специальности', name_kk: '', name_en: '' }]),
      specialtyJson, h('button', { type: 'submit', class: 'btn primary' }, 'Импортировать'));
    const specialtySelect = h('select', { 'aria-label': tr('Специальность') }, ...specialties.map((s) =>
      h('option', { value: String(s.id) }, rawText(s.name_ru))));
    const templateLocale = h('select', { 'aria-label': tr('Язык интерфейса') }, ...[['ru', 'Русский'], ['kk', 'Қазақша'], ['en', 'English']]
      .map(([code, label]) => h('option', { value: code }, label)));
    const templateType = documentTypePicker();
    const templateFields = h('textarea', { rows: '8', placeholder: '{"complaints":"Жалобы","diagnosis":"Диагноз"}' });
    const loadTemplate = async () => {
      if (!specialtySelect.value) { templateFields.value = ''; return; }
      const template = await api(`/catalog/specialties/${specialtySelect.value}/template?locale=${templateLocale.value}&document_type=${templateType.value}`);
      templateFields.value = JSON.stringify(template.fields, null, 2);
    };
    templateType.addEventListener('change', () => loadTemplate().catch((ex) => { notice.textContent = tr(ex.message); }));
    specialtySelect.addEventListener('change', () => loadTemplate().catch((ex) => { notice.textContent = tr(ex.message); }));
    templateLocale.addEventListener('change', () => loadTemplate().catch((ex) => { notice.textContent = tr(ex.message); }));
    const templateForm = h('form', { class: 'card', onsubmit: async (event) => {
      event.preventDefault(); notice.textContent = '';
      try {
        await api(`/catalog/specialties/${specialtySelect.value}/template`, {
          method: 'PUT', body: { document_type: templateType.value, locale: templateLocale.value, fields: JSON.parse(templateFields.value) },
        });
        toast('Шаблон сохранён');
      } catch (ex) { notice.textContent = ex instanceof SyntaxError ? 'Проверьте JSON шаблона' : ex.message; }
    } },
    h('h2', null, 'Шаблон медицинского документа'),
    specialties.length ? [specialtySelect, templateLocale, templateType,
      jsonFileInput((data) => {
        if (SUPPORTED_LOCALES.includes(data.locale)) templateLocale.value = data.locale;
        if (['initial', 'examination', 'discharge'].includes(data.document_type)) templateType.value = data.document_type;
        templateFields.value = JSON.stringify(data.fields || data, null, 2);
      }, (error) => { notice.textContent = error; }),
      exampleDownload('template.json', { locale: 'ru', document_type: 'initial', fields: { complaints: 'Жалобы', diagnosis: 'Диагноз', diagnosis_code: 'МКБ-10' } }),
      templateFields,
      h('p', { class: 'help' }, 'Поля: complaints, anamnesis, symptoms_duration, examination, diagnosis, diagnosis_code, treatment_plan, recommendations.'),
      h('button', { class: 'btn primary', type: 'submit' }, 'Сохранить шаблон')] :
      h('p', { class: 'muted' }, 'Сначала добавьте специальность.'));

    const icdJson = h('textarea', { rows: '12', placeholder: '[{"code":"J06.9","name_ru":"Острая инфекция верхних дыхательных путей неуточненная","name_kk":"","name_en":""}]' });
    const icdForm = h('form', { class: 'card', onsubmit: async (event) => {
      event.preventDefault(); notice.textContent = '';
      try {
        const items = JSON.parse(icdJson.value);
        if (!Array.isArray(items)) throw new SyntaxError('Ожидается JSON-массив кодов');
        const result = await api('/catalog/icd10', { method: 'PUT', body: items });
        toast(`${tr('Импортировано кодов:')} ${result.upserted}`);
      } catch (ex) { notice.textContent = ex instanceof SyntaxError ? 'Проверьте JSON-массив кодов МКБ-10' : ex.message; }
    } },
    h('h2', null, 'Импорт справочника МКБ-10'),
    h('p', { class: 'help' }, 'Загрузите проверенный JSON-массив. Каждая запись содержит code, name_ru и при наличии name_kk/name_en.'),
    jsonFileInput((data) => { icdJson.value = JSON.stringify(data, null, 2); }, (error) => { notice.textContent = error; }),
    exampleDownload('icd10.json', [{ code: 'J06.9', name_ru: 'Острая инфекция верхних дыхательных путей неуточненная', name_kk: '', name_en: '' }]),
    icdJson, h('button', { class: 'btn primary', type: 'submit' }, 'Импортировать'));
    loadTemplate().catch((ex) => { notice.textContent = tr(ex.message); });
    return h('div', { class: 'stack' }, notice, specialtyForm, specialtyImport, templateForm, icdForm);
  }

  async function auditTab() {
    const data = await api('/admin/audit?limit=200');
    return h('div', { class: 'scroll-x' }, h('table', { class: 'rows' },
      h('thead', null, h('tr', null, ['Время', 'Пользователь', 'Действие', 'Объект', 'Детали', 'IP'].map((t) => h('th', null, t)))),
      h('tbody', null, data.items.map((a) => h('tr', null, h('td', null, fmtDate(a.created_at)), h('td', null, a.user_email || '—'), h('td', null, a.action),
        h('td', null, a.entity_type ? `${a.entity_type} #${a.entity_id ?? ''}` : '—'), h('td', { class: 'small' }, a.details || ''), h('td', { class: 'small' }, a.ip_address || ''))))));
  }

  async function systemTab() {
    const s = await api('/admin/system');
    const row = (label, ok, extra) => h('tr', null, h('td', null, label), h('td', null, ok === null ? extra : h('span', { class: 'badge ' + (ok ? 'confirmed' : 'failed') }, ok ? 'Да' : 'Нет'), ok !== null && extra ? ' ' + extra : ''));
    return h('div', { class: 'stack' },
      h('table', { class: 'rows' }, h('tbody', null,
        row('Подтверждение email', s.email_verification_required),
        row('Двухфакторная аутентификация', s.two_factor_enabled),
        row('SMTP настроен', s.smtp_configured),
        row('Email-уведомления об изменении пароля', s.email_notifications_enabled),
        row('Распознавание речи', s.stt_key_configured, `${s.stt_provider}: ${s.stt_model}`),
        row('Языковая модель', s.llm_key_configured, s.llm_model),
        row('Диаризация (кто говорит)', s.diarization_enabled ? s.hf_token_configured : null, s.diarization_enabled ? '' : 'выключена, роли определяет языковая модель'),
        row('ffmpeg установлен', s.ffmpeg_available),
        row('Хранение аудио', null, s.audio_retention_days ? `${s.audio_retention_days} дн.` : 'без ограничения'),
        row('Удалять аудио после обработки', s.delete_audio_after_processing),
        row('Месячный лимит расходов', null, s.monthly_budget_usd ? '$' + s.monthly_budget_usd : 'не задан'))),
      h('div', null, h('button', { class: 'btn', onclick: async () => {
        try { const r = await api('/admin/retention/purge', { method: 'POST' }); toast(`${tr('Удалено записей:')} ${r.deleted_files}`); } catch (ex) { toast(ex.message, true); } } }, 'Удалить просроченные аудиозаписи сейчас')));
  }
}

/* ============ маршрутизация ============ */
function route() {
  if (state.token && hasUnsavedChanges?.() && !window.confirm(tr('Уйти без сохранения?'))) {
    history.replaceState(null, '', displayedHash);
    return;
  }
  hasUnsavedChanges = null;
  displayedHash = location.hash || '#/';
  if (cleanup) { cleanup(); cleanup = null; }
  const hash = location.hash || '#/';
  if (hash.startsWith('#/verify-email')) return verifyEmailPage();
  if (hash.startsWith('#/reset')) return passwordResetPage();
  if (!state.token) { if (hash !== '#/login') { location.hash = '#/login'; return; } return loginPage(); }
  if (hash === '#/login') { location.hash = '#/'; return; }
  let m;
  if (hash === '#/') return listPage();
  if (hash === '#/new') return newPage();
  if ((m = hash.match(/^#\/c\/(\d+)$/))) return detailPage(Number(m[1]));
  if (hash === '#/admin' && state.user.role === 'admin') return adminPage();
  location.hash = '#/';
}
window.addEventListener('hashchange', route);
route();
