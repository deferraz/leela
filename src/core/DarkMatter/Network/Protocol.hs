{-# LANGUAGE OverloadedStrings #-}
-- All Rights Reserved.
--
--    Licensed under the Apache License, Version 2.0 (the "License");
--    you may not use this file except in compliance with the License.
--    You may obtain a copy of the License at
--
--        http://www.apache.org/licenses/LICENSE-2.0
--
--    Unless required by applicable law or agreed to in writing, software
--    distributed under the License is distributed on an "AS IS" BASIS,
--    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
--    See the License for the specific language governing permissions and
--    limitations under the License.

module DarkMatter.Network.Protocol where

import qualified Data.ByteString as B
import           Network.Socket (Socket)
import           Network.Socket.ByteString

recvFrame :: Socket -> IO B.ByteString
recvFrame = flip recv 65536

sendFrame :: Socket -> B.ByteString -> IO ()
sendFrame s msg = send s msg >> return ()
                       

