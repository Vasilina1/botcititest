from gspread_asyncio import AsyncioGspreadClient, AsyncioGspreadWorksheet

# For test
# import asyncio
#
# import gspread
# import gspread_asyncio
# from google.oauth2.service_account import Credentials  # For test
#
# def get_scoped_credentials(credentials, scopes):
#     def prepare_credentials():
#         return credentials.with_scopes(scopes)
#
#     return prepare_credentials
#
# scopes = [
#     "https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
#     "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"
# ]
# google_credentials = Credentials.from_service_account_file("google_sheets/creds.json")
# scoped_credentials = get_scoped_credentials(google_credentials, scopes)
# google_client_manager = gspread_asyncio.AsyncioGspreadClientManager(
#     scoped_credentials
# )
#
#
# async def get_autorize_google_client():
#     google_client = await google_client_manager.authorize()
#     return google_client


# End for test


async def get_worksheet(client: AsyncioGspreadClient) -> AsyncioGspreadWorksheet:
    spreadsheet = await client.open_by_key("1dC443WLoRyKSGBoGf1wxvOBd4ZK7Dulyr5eDDUd1KI0")
    worksheet = await spreadsheet.get_worksheet(0)
    return worksheet


async def get_data_from_range(worksheet: AsyncioGspreadWorksheet, range_cells: str, major_dimension: str) -> list[list]:
    data = await worksheet.get_values(range_cells, major_dimension)
    return data


# Run for test
# async def main():
#     google_client = await get_autorize_google_client()
#     worksheet = await get_worksheet(google_client)
#     data = await get_data_from_range(worksheet, "A2:A", "COLUMNS")
#     print(data)



# asyncio.run(main())