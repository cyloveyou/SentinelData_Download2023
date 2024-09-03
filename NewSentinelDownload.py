# _*_coding:utf-8_*_
# created by cy on 2023/11/12
# 公众号:小y只会写bug
# CSDN主页:https://blog.csdn.net/weixin_64989228?spm=1000.2115.3001.5343

import multiprocessing
import os
import random
import re
import shutil
import time

import requests
from tqdm import tqdm, trange


class SentinelDownload:
	def __init__(self, UserName, Password, SearchUrl, Proxies):
		self.userName = UserName  # 用户名
		self.password = Password  # 密码
		self.SearchUrl = self.CreatURL(SearchUrl)  # 构造检索url
		self.proxies = Proxies  # 代理

		self.tokenStr = self.GetAccessToken()  # 获取token
		self.SearchResList = self.Search()  # 检索数据

	def CreatURL(self, urlStr: str) -> str:
		return urlStr.strip()

	def GetAccessToken(self) -> str:
		"""
		获取token,用于下载数据
		:return:
		"""
		data = {
			"client_id": "cdse-public",
			"username": self.userName,
			"password": self.password,
			"grant_type": "password",
		}
		try:
			r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
							  data=data, proxies=self.proxies)
			print("token获取成功！")
			return r.json()["access_token"]
		except Exception as e:
			print(f"获取token时捕获到异常{e}")
			# t = random.randint(20, 60)
			t = 15 # 修改为15秒,等半分钟也太折磨了
			print(f"Access token creation failed. 等待{t}s,随后重新获取token...")
			for _ in trange(t):
				time.sleep(1)
			self.GetAccessToken()

	def Search(self) -> list:
		"""
		检索数据
		"""
		SearchResult = []
		res = requests.get(self.SearchUrl, proxies=self.proxies)
		jsonInfo = res.json()
		res.close()  # 关闭连接
		n = jsonInfo["@odata.count"]  # 检索到的数据总数
		if n == 0:
			print("没有检索到数据")
		else:
			print(f"共检索到{n}条数据，开始进行数据信息的采集")
			r = 900  # 单次采集条数，在1-1000之间
			for k in range(0, n, r):
				print(f"正在进行第{k}-{k + r}数据信息的采集")
				top = re.findall(r"(top=\d+)", self.SearchUrl)[0]
				skip = re.findall(r"(skip=\d+)", self.SearchUrl)[0]
				url = self.SearchUrl.replace(top, f"top={900}").replace(skip, f"skip={k}")  # 修正url
				jsonInfo = requests.get(url, proxies=self.proxies).json() # 捉虫
				SearchResult += [{"Id": i["Id"], "Name": i["Name"]} for i in jsonInfo['value']]
		# 检索数据
		print(f"数据采集完成，共采集到{len(SearchResult)}条数据信息")
		return SearchResult

	def Download1(self, DownloadInfo: list):
		"""
		单个数据文件的下载，如果文件存在，则返回
		:param DownloadInfo:(productID, savePath,tempPath)
		:return:
		"""
		productID, savePath, tempPath = DownloadInfo
		time.sleep(random.uniform(0, 3))
		if os.path.exists(f'{savePath}.zip'):
			print(f"{savePath}.zip 已经存在，跳过下载")
			return
		url = f"http://zipper.dataspace.copernicus.eu/odata/v1/Products({productID})/$value"
		headers = {"Authorization": f"Bearer {self.tokenStr}"}  # 设置token
		try:
			response = requests.get(url, headers=headers, stream=True, proxies=self.proxies, timeout=10)
			if response.status_code == 200:
				data_size = round(float(response.headers['Content-Length'])) / 1024 / 1024

				with open(f'{tempPath}.zip', 'wb') as f:
					for data in tqdm(iterable=response.iter_content(1024 * 1024), total=int(data_size),
									 desc=f'{tempPath}.zip', unit='MB'):
						f.write(data)
				shutil.move(f'{tempPath}.zip', f'{savePath}.zip')
				print(f"{savePath}.zip下载完成")
				response.close()  # 关闭连接
			else:
				print(f"响应状态码错误{response.status_code},返回内容：{response.text}")
				if os.path.exists(f'{savePath}.zip'):
					os.remove(f'{savePath}.zip')
				t = random.randint(20, 60)
				print(f"{savePath}下载失败,尝试更新token并等待{t}s,随后重新下载...")
				for _ in trange(t):
					time.sleep(1)

				self.tokenStr = self.GetAccessToken()
				self.Download1(DownloadInfo)
		except Exception as e:
			print("捕获到异常:", e)
			if os.path.exists(f'{savePath}.zip'):
				os.remove(f'{savePath}.zip')
			t = random.randint(20, 60)
			print(f"{savePath}下载失败,尝试更新token并等待{t}s,随后重新下载...")
			for _ in trange(t):
				time.sleep(1)

			self.tokenStr = self.GetAccessToken()
			self.Download1(DownloadInfo)

	def SingleDownload(self, saveFolder):
		"""
		单线程下载数据
		"""
		print(f"开始进行单线程数据的下载...")
		# 创建一个合适的路径
		if not os.path.exists(f"{saveFolder}/Finish"):
			os.makedirs(f"{saveFolder}/Finish")
		if not os.path.exists(f"{saveFolder}/Temp"):
			os.makedirs(f"{saveFolder}/Temp")
		# 循环下载
		for i in range(len(self.SearchResList)):
			ID = self.SearchResList[i]['Id']
			Name = self.SearchResList[i]['Name']
			savePath = f"{saveFolder}/Finish/{Name}"
			tempPath = f"{saveFolder}/Temp/{Name}"

			InfoLi = [ID, savePath, tempPath]
			self.Download1(InfoLi)

	def MultiDownload(self, saveFolder: str, poolNum: int = 2) -> None:
		"""
		多线程下载数据
		:param poolNum:
		:param saveFolder:
		:return:
		"""
		print(f"开始进行多线程数据的下载,线程数为{poolNum}...")

		if not os.path.exists(f"{saveFolder}/Finish"):
			os.makedirs(f"{saveFolder}/Finish")
		if not os.path.exists(f"{saveFolder}/Temp"):
			os.makedirs(f"{saveFolder}/Temp")

		Li = []
		for i in range(len(self.SearchResList)):
			ID = self.SearchResList[i]['Id']
			Name = self.SearchResList[i]['Name']

			savePath = f"{saveFolder}/Finish/{Name}"
			tempPath = f"{saveFolder}/Temp/{Name}"

			InfoLi = [ID, savePath, tempPath]
			Li.append(InfoLi)

		pool = multiprocessing.Pool(poolNum)  # 可以设置线程数，不宜过大
		pool.map(self.Download1, Li)


if __name__ == '__main__':
	# todo 设置参数
	IPPort = "替换位置一:替换位置二"  # todo 设置代理

	Folder = r"./SentinelTest"  # todo 保存路径
	userName = "xxxxxx"  # todo 用户名
	password = "xxxxxx"  # todo 密码

	proxies = {
		"http": IPPort,
		"https": IPPort
	}
	# 读取urlString
	with open("SearchURL.txt", mode="r") as f:
		urlString = f.read()  # 网页获取的url,顾及到url过长，故存放在txt文件中

	# 初始化配置
	SL = SentinelDownload(UserName=userName, Password=password, Proxies=proxies, SearchUrl=urlString)
	# 下载数据
	SL.MultiDownload(saveFolder=Folder)  # 多进程
# SL.SingleDownload(saveFolder=Folder)  # 单线程
