"""Schema xác thực và tài khoản dùng chung."""

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class AccountPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    email_verified: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    account: AccountPublic


class TokenData(BaseModel):
    user_id: int | None = None
    role: str | None = None


class CandidateRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Họ tên phải có ít nhất 2 ký tự.")

        return value


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)


class VerifyEmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(max_length=255)

    otp: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$",
    )