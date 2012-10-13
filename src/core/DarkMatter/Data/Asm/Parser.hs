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

-- | The language that is used to communicate with the core. The
-- parser should be able to recognize the following grammar (ABNF):
-- 
--   S      = PROC
--          / EVENT
--          / CLOSE
--   PROC   = "proc" SP PIPELINE EOL
--   PIPELINE = FUNC *(SP "|" SP FUNC)
--   EVENT  = "event" SP KEY SP TIME SP VAL EOL
--   CLOSE  = "close" EOL
--   EOL    = ";"
--   WINDOW = "window" SP 1*DIGIT 1*DIGIT
--   MAP    = "map"
--   KEY    = 1*DIGIT "|" ALPHANUM
--   TIME   = 1*DIGIT "." 1*DIGIT
--   VAL    = 1*DIGIT "." 1*DIGIT
--   FUNC   = "(" ARITHF ")"
--          / "window" SP 1*DIGIT "(" PIPELINE ")"
--          / "sum"
--          / "prod"
--          / "id"
--          / "truncate"
--          / "ceil"
--          / "floor"
--          / "round"
--          / "abs"
--          / "mean"
--          / "median"
--          / "maximum"
--          / "mininmum"
--   ARITHF = OP SP VAL
--   OP     = "*"
--          / "/"
--          / "+"
--          / "-"
module DarkMatter.Data.Asm.Parser
       ( runOne
       , runAll
       , asmParser
       ) where

import Debug.Trace
import           Control.Monad
import           Data.Attoparsec.ByteString as P
import qualified Data.Attoparsec.ByteString.Char8 as P8
import qualified Data.ByteString as B
import           DarkMatter.Data.Asm.Types
import           DarkMatter.Data.Time

nan :: Double
nan = 0 / 0

inf :: Double
inf = 1 / 0

ninf :: Double
ninf = - inf

asmParser :: Parser Asm
asmParser = do { mc <- P8.peekChar
               ; case mc
                 of Just 'e' -> parseEvent
                    Just 'p' -> parseProc
                    Just 'c' -> parseClose
                    _        -> fail ("error: e|c|p were expected")
               }

endBy :: Parser a -> Parser () -> Parser a
endBy m s = do { r <- m
               ; _ <- s
               ; return r
               }

runOne :: B.ByteString -> Maybe Asm
runOne i = either (const Nothing) Just (parseOnly (asmParser `endBy` eol) i)

runAll :: B.ByteString -> [Asm]
runAll i = either (const []) id (parseOnly parser i)
  where parser = do { eof <- atEnd
                    ; if eof
                      then return []
                      else liftM2 (:) (asmParser `endBy` eol) parser
                    }

eol :: Parser ()
eol = P8.char ';' >> return ()

parseInt :: Parser Int
parseInt = P8.decimal

parseKey :: Parser B.ByteString
parseKey = do { n <- parseInt
              ; _ <- P8.char '|'
              ; P.take n
              }

parseTime :: Parser Time
parseTime = do { s <- parseInt
               ; _ <- P8.char '.'
               ; n <- parseInt
               ; return (mktime s n)
               }

parseVal :: Parser Double
parseVal = do { c <- P8.peekChar
              ; case c
                of Just 'n' -> string "nan" >> return nan
                   Just 'i' -> string "inf" >> return inf
                   Just '-' -> choice [ P8.rational
                                      , string "-inf" >> return ninf
                                      ]
                   _        -> P8.rational
              }

parseClose :: Parser Asm
parseClose = P8.string "close" >> return Close

parseEvent :: Parser Asm
parseEvent = do { _   <- string "event "
                ; key <- parseKey
                ; _   <- P8.space
                ; col <- parseTime
                ; _   <- P8.space
                ; val <- parseVal
                ; return (Event key col val)
                }

parseProc :: Parser Asm
parseProc = do { _         <- string "proc "
               ; pipeline  <- parseFunction `sepBy` string " | "
               ; return (Proc pipeline)
               }

parseWindow :: Parser AsyncFunc
parseWindow = do { _ <- string "window "
                 ; n <- parseInt
                 ; _ <- P8.space
                 ; _ <- P8.char '('
                 ; p <- parseSyncFunc `sepBy` string " | "
                 ; _ <- P8.char ')'
                 ; return (Window n p)
                 }

parseSyncFunc :: Parser SyncFunc
parseSyncFunc = do { c <- P8.peekChar
                   ; case c
                     of Just 'a' -> string "abs" >> return Abs
                        Just 'c' -> string "ceil" >> return Ceil
                        Just 'f' -> string "floor" >> return Floor
                        Just 'i' -> string "id" >> return Id
                        Just 'm' -> choice [ string "mean"     >> return Mean
                                           , string "median"   >> return Median
                                           , string "minimum"  >> return Minimum
                                           , string "maximum"  >> return Maximum
                                           ]
                        Just 'p' -> string "prod" >> return Prod
                        Just 'r' -> string "round" >> return Round
                        Just 's' -> string "sum"  >> return Sum
                        Just 't' -> string "truncate" >> return Truncate
                        Just '(' -> parseArithmetic
                        _        -> fail "error: a|c|f|m|p|r|s|t|( were expected"
                   }

parseAsyncFunc :: Parser AsyncFunc
parseAsyncFunc = do { mc <- P8.peekChar
                    ; case mc
                      of Just 's' -> choice [ parseSMA
                                            , parseSample
                                            ]
                         Just 'w' -> parseWindow
                         _        -> fail "parseAsyncFunc: s|w were expected"
                    }

parseFunction :: Parser Function
parseFunction = do { c <- P8.peekChar
                   ; case c
                     of Just 's' -> choice [ fmap Left parseAsyncFunc
                                           , fmap Right parseSyncFunc
                                           ]
                        Just 'w' -> fmap Left parseAsyncFunc
                        _        -> fmap Right parseSyncFunc
                   }

parseSMA :: Parser AsyncFunc
parseSMA = do { _ <- string "sma "
              ; liftM SMA parseInt
              }

parseSample :: Parser AsyncFunc
parseSample = do { _ <- string "sample "
                 ; n <- parseInt
                 ; _ <- P8.char '/'
                 ; m <- parseInt
                 ; return (Sample n m)
                 }

parseOp :: Parser ArithOp
parseOp = do { c <- P8.satisfy (`elem` "*+/-")
             ; case c
               of '*' -> return Mul
                  '+' -> return Add
                  '/' -> return Div
                  '-' -> return Sub
                  _   -> fail "error: *|+|-|/ were expected"
             }

parseArithmetic :: Parser SyncFunc
parseArithmetic = do { _ <- P8.char '('
                     ; o <- parseOp
                     ; _ <- P8.space
                     ; v <- parseVal
                     ; _ <- P8.char ')'
                     ; return (Arithmetic o v)
                     }
