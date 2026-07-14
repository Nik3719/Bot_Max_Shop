# Тексты для регистрации
REG_WELCOME = "Добро пожаловать в MAX-магазин! 👋\nПожалуйста, введите ваше имя (от 2 до 60 символов, только буквы)."
REG_INVALID_NAME = "Имя должно содержать только буквы, от 2 до 60 символов. Попробуйте снова."
REG_ASK_PHONE = "Отлично! Теперь укажите ваш номер телефона (в формате +7XXXXXXXXXX или 8XXXXXXXXXX)."
REG_INVALID_PHONE = "Введите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX."
REG_PHONE_EXISTS = "Этот номер телефона уже зарегистрирован. Пожалуйста, укажите другой или обратитесь в поддержку."
REG_ERROR = "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
REG_SUCCESS = "Вы успешно зарегистрированы! 🎉"
REG_ALREADY = "Вы уже зарегистрированы в нашем магазине. Приятных покупок!"

ACCESS_DENIED = "Доступ запрещен. Пожалуйста, зарегистрируйтесь, отправив команду /start"

# Админ
ADMIN_ONLY = "⛔ Команда доступна только администраторам."
SYNC_STARTED = "🔄 Запущена синхронизация с Google Sheets..."

# Сообщения магазина
HELP_USER = """📖 Доступные команды:

/start — Главное меню
/myorders — Мои заявки
/help — Эта справка

🛍 Лента товаров — кнопка в меню
📋 Мои заявки — кнопка в меню"""

HELP_ADMIN = """🔧 Команды администратора:

📦 Синхронизация:
/sync_from_sheets — Загрузить товары из Google Sheets
/sync_to_sheets — Выгрузить заявки в Google Sheets
/sync_status — Статус последней синхронизации

📊 Управление:
/orders — Новые заявок (принять / отклонить)
/orders_all — Список всех заявок (последние 20)
/stats — Статистика (пользователи, товары, заявки)
/help — Эта справка"""
UNKNOWN_CMD = "Неизвестная команда. Введите /help для списка команд."
SPAM_WARNING = "Вы отправляете сообщения слишком часто. Пожалуйста, подождите немного."
NO_PRODUCTS = "На данный момент товаров нет в наличии."
ASK_COMMENT = "Укажите удобное время звонка или любой комментарий. Нажмите /skip чтобы пропустить."

# Шаблоны
def format_product(p: dict) -> str:
    return f"📱 {p['name']}\n─────────────────────────────\n{p['description']}\n\n💰 {p['price']} ₽\n🏷 {p.get('category', 'Без категории')}"

def format_order_admin(o: dict) -> str:
    cat = o.get('category') or 'Без категории'
    photo = f"📷 Фото: {o['photo_url']}" if o.get('photo_url') else "📷 Фото недоступно"
    
    return f"🛒 НОВАЯ ЗАЯВКА #{o['id']}\n──────────────────────────────\n📦 Товар:   {o['product_name']}\n💰 Цена:    {o['price']} ₽\n🏷 Категория: {cat}\n{photo}\n\n👤 Покупатель: {o['full_name']}\n📞 Телефон:    {o['phone']}\n🆔 MAX ID:     {o['max_user_id']}\n\n💬 Комментарий: {o['comment']}\n\n🕐 Время заявки: {o['created_at']}\n──────────────────────────────"

ORDER_DATA_ERROR = "Произошла ошибка при получении данных. Попробуйте еще раз."
ORDER_CONFIRM_PROMPT = "Пожалуйста, подтвердите или отмените заявку с помощью кнопок выше."
ORDER_NOT_FOUND_NOTIF = "Ошибка: данные о товаре не найдены. Попробуйте начать заново."
ORDER_NOT_FOUND_MSG = "Ошибка: данные о товаре не найдены. Попробуйте начать заново."
ORDER_CREATED_NOTIF = "Заявка оформлена!"
ORDER_CREATED_MSG = "✅ Заявка #{order_id} оформлена! Мы свяжемся с вами по номеру {phone}. Ожидайте звонка."
ORDER_CREATE_ERROR = "Ошибка при создании заявки."
ORDER_CANCELLED_NOTIF = "Отменено"
ORDER_CANCELLED_MSG = "❌ Оформление заявки отменено."

def format_final_card(product_name: str, price: int, user_name: str, phone: str, comment: str) -> str:
    return (
        "📋 Итоговая карточка заказа\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {price} ₽\n\n"
        f"👤 Имя: {user_name}\n"
        f"📞 Телефон: {phone}\n"
        f"💬 Комментарий: {comment or 'Нет'}\n\n"
        "Подтверждаете оформление заявки?"
    )

ADMIN_NO_ACCESS_NOTIF = "Нет прав"
ADMIN_ORDER_NOT_FOUND_NOTIF = "Заявка не найдена"
ADMIN_ORDER_ALREADY_ACCEPTED = "Эта заявка уже ПРИНЯТА другим администратором (или вами)!"
ADMIN_ORDER_ALREADY_REJECTED = "Эта заявка уже ОТКЛОНЕНА!"
ADMIN_ORDER_ALREADY_PROCESSED = "Эта заявка уже обработана!"
ADMIN_ORDER_STATUS_CHANGED = "Заявка #{order_id} переведена в статус {status}."

USER_ORDER_ACCEPTED = "🎉 Ваша заявка #{order_id} на «{p_name}» принята! С вами свяжутся в ближайшее время."
USER_ORDER_REJECTED = "😔 Заявка #{order_id} на «{p_name}» отклонена. Для уточнения деталей обратитесь к администратору."

PRODUCT_NOT_FOUND_OR_DELETED = "Товар не найден или удален."
ORDERING_PROCESS_NOTIF = "Оформление заявки..."
ORDERING_PROMPT = "Вы оформляете заявку на: {p_name}\n\n{ask_comment}"
UNKNOWN_PHONE = "Неизвестно"
ACTION_ALREADY_CANCELLED = "Действие уже отменено"
