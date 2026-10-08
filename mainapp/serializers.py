from rest_framework import serializers
from .models import User, Category, ExpenseCategory, Wallet, Member, Income, Expense, Transfer, Debt


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "date_joined",
            "password",
        ]
        # status faqat admin panel / soft delete orqali o'zgaradi
        read_only_fields = ["id", "date_joined", "status"]

    def validate_email(self, value):
        # Email bilan ham kirish mumkin — shuning uchun ikki akkauntda bir xil email bo'lmasin
        if value and User.email_taken(value, exclude_pk=getattr(self.instance, "pk", None)):
            raise serializers.ValidationError("Bu email boshqa akkauntda ishlatilgan")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        # Parol bu yerda o'zgartirilmaydi: aks holda u shifrlanmasdan saqlanib qoladi
        # va joriy parolni tekshirish chetlab o'tiladi
        if "password" in validated_data:
            raise serializers.ValidationError({
                "password": "Parolni /api/v1/auth/change-password/ orqali o'zgartiring"
            })
        return super().update(instance, validated_data)


class CategorySerializer(serializers.ModelSerializer):
    """Daromad turlari serializeri"""
    class Meta:
        model = Category
        fields = ["id", "name", "description", "icon", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Harajat turlari serializeri"""
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "description", "icon", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class WalletSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "name",
            "summa",
            "currency",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_summa(self, value):
        if value < 0:
            raise serializers.ValidationError("Hamyon boshlang'ich balansi manfiy bo'lishi mumkin emas")
        return value

    def validate(self, attrs):
        # Balansni faqat Daromad/Harajat/O'tkazma orqali o'zgartirish mumkin —
        # mavjud hamyonning summasini to'g'ridan-to'g'ri tahrirlashga yo'l qo'yilmaydi
        if self.instance is not None and "summa" in attrs and attrs["summa"] != self.instance.summa:
            raise serializers.ValidationError({
                "summa": "Hamyon balansini to'g'ridan-to'g'ri o'zgartirib bo'lmaydi. "
                         "Daromad, Harajat yoki O'tkazma orqali o'zgartiring."
            })
        return attrs


class MemberSerializer(serializers.ModelSerializer):
    """Oila a'zolari / yaqinlar serializeri"""
    class Meta:
        model = Member
        fields = ["id", "name", "kind", "status", "created_at"]
        read_only_fields = ["id", "created_at"]


class IncomeSerializer(serializers.ModelSerializer):
    """Daromad serializeri"""
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Income
        fields = [
            "id",
            "wallet",
            "wallet_name",
            "summa",
            "category",
            "category_name",
            "description",
            "date",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("Daromad summasi 0 dan katta bo'lishi shart")
        return value

    def validate(self, attrs):
        wallet = attrs.get("wallet") or getattr(self.instance, "wallet", None)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else (attrs.get("user") or getattr(self.instance, "user", None))
        summa = attrs.get("summa") if "summa" in attrs else getattr(self.instance, "summa", 0)

        if wallet and user and wallet.user_id != user.id:
            raise serializers.ValidationError({"wallet": "Tanlangan hamyon ushbu foydalanuvchiga tegishli emas"})

        category = attrs.get("category") or getattr(self.instance, "category", None)
        if category and user and category.user_id not in (None, user.id):
            raise serializers.ValidationError({"category": "Tanlangan kategoriya sizga tegishli emas"})

        if self.instance and wallet and summa:
            if self.instance.wallet_id == wallet.id and self.instance.summa > summa:
                diff = self.instance.summa - summa
                if wallet.summa < diff:
                    raise serializers.ValidationError({
                        "summa": f"Daromadni kamaytirish uchun hamyonda yetarli mablag' qolmagan (Hamyon balansi: {wallet.summa:,} {wallet.currency})"
                    })
        return attrs


class ExpenseSerializer(serializers.ModelSerializer):
    """Harajat serializeri — nima narsaga, qayerda, qachon"""
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    member_name = serializers.CharField(source="member.name", read_only=True, default=None)
    member_kind = serializers.CharField(source="member.kind", read_only=True, default=None)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "category",
            "category_name",
            "summa",
            "wallet",
            "wallet_name",
            "member",
            "member_name",
            "member_kind",
            "location",
            "description",
            "date",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("Harajat summasi 0 dan katta bo'lishi shart")
        return value

    def validate(self, attrs):
        wallet = attrs.get("wallet") or getattr(self.instance, "wallet", None)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else (attrs.get("user") or getattr(self.instance, "user", None))
        summa = attrs.get("summa") if "summa" in attrs else getattr(self.instance, "summa", 0)

        if wallet and user and wallet.user_id != user.id:
            raise serializers.ValidationError({"wallet": "Tanlangan hamyon ushbu foydalanuvchiga tegishli emas"})

        category = attrs.get("category") or getattr(self.instance, "category", None)
        if category and user and category.user_id not in (None, user.id):
            raise serializers.ValidationError({"category": "Tanlangan kategoriya sizga tegishli emas"})

        member = attrs.get("member") or getattr(self.instance, "member", None)
        if member and user and member.user_id != user.id:
            raise serializers.ValidationError({"member": "Tanlangan a'zo ushbu foydalanuvchiga tegishli emas"})

        if wallet and summa:
            if self.instance is None:
                if wallet.summa < summa:
                    raise serializers.ValidationError({
                        "summa": f"Hamyonda mablag' yetarli emas! Mavjud balans: {wallet.summa:,} {wallet.currency}"
                    })
            else:
                old_summa = self.instance.summa if self.instance.wallet_id == wallet.id else 0
                required_balance = summa - old_summa
                if required_balance > 0 and wallet.summa < required_balance:
                    raise serializers.ValidationError({
                        "summa": f"Hamyonda mablag' yetarli emas! Qo'shimcha zarur: {required_balance:,} {wallet.currency}, mavjud: {wallet.summa:,} {wallet.currency}"
                    })
        return attrs


class TransferSerializer(serializers.ModelSerializer):
    """Hamyonlararo o'tkazma serializeri"""
    from_wallet_name = serializers.CharField(source="from_wallet.name", read_only=True)
    to_wallet_name = serializers.CharField(source="to_wallet.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "id",
            "from_wallet",
            "from_wallet_name",
            "to_wallet",
            "to_wallet_name",
            "summa",
            "description",
            "date",
            "user",
            "user_name",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_summa(self, value):
        if value <= 0:
            raise serializers.ValidationError("O'tkazma summasi 0 dan katta bo'lishi kerak")
        return value

    def validate(self, attrs):
        from_wallet = attrs.get("from_wallet") or getattr(self.instance, "from_wallet", None)
        to_wallet = attrs.get("to_wallet") or getattr(self.instance, "to_wallet", None)
        summa = attrs.get("summa") if "summa" in attrs else getattr(self.instance, "summa", 0)

        if from_wallet and to_wallet and from_wallet.id == to_wallet.id:
            raise serializers.ValidationError({"to_wallet": "Bir xil hamyonlar o'rtasida o'tkazma qilib bo'lmaydi"})

        if from_wallet and summa:
            if self.instance is None:
                if from_wallet.summa < summa:
                    raise serializers.ValidationError({
                        "summa": f"O'tkazish uchun hamyonda yetarli mablag' yo'q! Mavjud: {from_wallet.summa:,} {from_wallet.currency}"
                    })
            else:
                old_summa = self.instance.summa if self.instance.from_wallet_id == from_wallet.id else 0
                required_balance = summa - old_summa
                if required_balance > 0 and from_wallet.summa < required_balance:
                    raise serializers.ValidationError({
                        "summa": f"O'tkazish uchun hamyonda yetarli mablag' yo'q! Mavjud: {from_wallet.summa:,} {from_wallet.currency}"
                    })
        return attrs


class DebtSerializer(serializers.ModelSerializer):
    """Qarzlar daftari serializeri"""
    wallet_name = serializers.CharField(source="wallet.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    remaining_summa = serializers.IntegerField(read_only=True)

    class Meta:
        model = Debt
        fields = [
            "id",
            "user",
            "user_name",
            "person_name",
            "debt_type",
            "summa",
            "paid_summa",
            "remaining_summa",
            "wallet",
            "wallet_name",
            "due_date",
            "description",
            "is_settled",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "remaining_summa", "created_at", "updated_at"]

    def validate(self, attrs):
        summa = attrs.get("summa", getattr(self.instance, "summa", 0))
        paid_summa = attrs.get("paid_summa", getattr(self.instance, "paid_summa", 0))
        if summa <= 0:
            raise serializers.ValidationError({"summa": "Qarz summasi musbat bo'lishi kerak"})
        if paid_summa > summa:
            raise serializers.ValidationError({"paid_summa": "Qaytarilgan summa umumiy qarzdan ko'p bo'lishi mumkin emas"})
        if paid_summa == summa:
            attrs["is_settled"] = True

        debt_type = attrs.get("debt_type", getattr(self.instance, "debt_type", None))
        wallet = attrs.get("wallet", getattr(self.instance, "wallet", None))
        if self.instance is None and wallet and debt_type == "give":
            if wallet.summa < summa:
                raise serializers.ValidationError({
                    "wallet": f"Qarz berish uchun hamyonda yetarli mablag' yo'q! Mavjud: {wallet.summa:,} {wallet.currency}"
                })
        return attrs
